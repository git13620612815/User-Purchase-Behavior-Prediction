import csv
import io
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.common import ok, page_args
from app.api.users import user_dict
from app.constants import BEHAVIOR_LABEL
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.errors import AppError
from app.core.security import PASSWORD_RE, USERNAME_RE, hash_password
from app.graph.registry import registry
from app.graph.state import graph_state
from app.models.tables import Behavior, Category, ModelVersion, Prediction, PredictionItem, Product, TrainJob, User
from app.services.behavior_service import behavior_dict, rebuild_stats
from app.services.import_service import clean_behaviors, commit_batch, preview_rows, save_preview
from app.services.predict_service import batch_predict, predict_for_user, prediction_analysis, _prediction_payload
from app.services.graph_view import graph_summary
from app.services.stats_service import overview, product_stats, user_analysis
from app.services.train_service import start_compare, start_train

router = APIRouter(prefix="/admin", tags=["admin"])


class UserBody(BaseModel):
    username: str
    password: str
    nickname: str | None = None
    gender: str | None = "未知"
    age: int | None = None
    phone: str | None = None
    email: str | None = None
    role: str = "USER"


class UserUpdate(BaseModel):
    nickname: str | None = None
    gender: str | None = None
    age: int | None = None
    phone: str | None = None
    email: str | None = None
    role: str | None = None


class StatusBody(BaseModel):
    status: str


class ProductBody(BaseModel):
    skuCode: str
    name: str
    categoryName: str
    price: float
    status: str = "ON"


class TrainBody(BaseModel):
    algorithm: str = "HETERO_SAGE"
    learningRate: float = 0.001
    batchSize: int = 1024
    epochs: int = 30


class CompareGroup(BaseModel):
    learningRate: float = 0.001
    batchSize: int = 1024
    epochs: int = 10


class CompareBody(BaseModel):
    algorithms: list[str] = Field(default_factory=lambda: ["HETERO_SAGE", "GCN", "GAT"])
    groups: list[CompareGroup] | None = None
    learningRate: float = 0.001
    batchSize: int = 1024
    epochs: int = 10


class BatchBody(BaseModel):
    userIds: list[int] = Field(default_factory=list)
    keyword: str | None = None


@router.get("/users")
def list_users(keyword: str | None = None, page: int = 1, pageSize: int = 10, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    page, page_size = page_args(page, pageSize)
    query = db.query(User)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter((User.username.like(like)) | (User.nickname.like(like)))
    total = query.count()
    rows = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({"total": total, "page": page, "pageSize": page_size, "items": [user_dict(row) for row in rows]})


@router.post("/users")
def create_user(body: UserBody, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if not USERNAME_RE.match(body.username) or not PASSWORD_RE.match(body.password):
        raise AppError(40001, "用户名或密码不符合规则")
    if body.role not in ("USER", "ADMIN"):
        raise AppError(40001, "角色不合法")
    if db.query(User).filter(User.username == body.username).first():
        raise AppError(40001, "用户名已存在")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname or body.username,
        gender=body.gender or "未知",
        age=body.age,
        phone=body.phone,
        email=body.email,
        role=body.role,
        status="ENABLED",
    )
    db.add(user)
    db.commit()
    return ok(user_dict(user))


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise AppError(40401, "用户不存在", 404)
    if body.role is not None and body.role not in ("USER", "ADMIN"):
        raise AppError(40001, "角色不合法")
    for field, attr in (("nickname", "nickname"), ("gender", "gender"), ("age", "age"), ("phone", "phone"), ("email", "email"), ("role", "role")):
        value = getattr(body, field)
        if value is not None:
            setattr(user, attr, value)
    db.commit()
    return ok(user_dict(user))


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise AppError(40401, "用户不存在", 404)
    if user.id == admin.id:
        raise AppError(40001, "不能删除当前登录管理员")
    used = db.query(Behavior).filter(Behavior.user_id == user.id).first() or db.query(Prediction).filter(Prediction.user_id == user.id).first()
    if used:
        user.status = "DISABLED"
        db.commit()
        return ok({"disabled": True}, "已有行为记录，已改为停用")
    db.delete(user)
    db.commit()
    return ok({"deleted": True})


@router.put("/users/{user_id}/status")
def update_status(user_id: int, body: StatusBody, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if body.status not in ("ENABLED", "DISABLED"):
        raise AppError(40001, "状态不合法")
    user = db.get(User, user_id)
    if user is None:
        raise AppError(40401, "用户不存在", 404)
    if user.id == admin.id and body.status == "DISABLED":
        raise AppError(40001, "不能停用当前登录管理员")
    user.status = body.status
    db.commit()
    return ok(user_dict(user))


@router.get("/products")
def admin_products(keyword: str | None = None, page: int = 1, pageSize: int = 10, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    page, page_size = page_args(page, pageSize)
    query = db.query(Product, Category).join(Category, Category.id == Product.category_id)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter((Product.name.like(like)) | (Product.sku_code.like(like)))
    total = query.count()
    rows = query.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": [{
            "id": product.id,
            "skuCode": product.sku_code,
            "name": product.name,
            "categoryName": category.name,
            "price": float(product.price or 0),
            "status": product.status,
        } for product, category in rows],
    })


def _check_product(body: ProductBody) -> None:
    if not body.skuCode.strip() or not body.name.strip() or not body.categoryName.strip():
        raise AppError(40001, "商品编号、名称和类目不能为空")
    if body.price < 0:
        raise AppError(40001, "价格不能小于 0")
    if body.status not in ("ON", "OFF"):
        raise AppError(40001, "商品状态不合法")
    body.skuCode = body.skuCode.strip()
    body.name = body.name.strip()
    body.categoryName = body.categoryName.strip()


@router.post("/products")
def create_product(body: ProductBody, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    _check_product(body)
    if db.query(Product).filter(Product.sku_code == body.skuCode).first():
        raise AppError(40012, "商品编号已存在")
    category = db.query(Category).filter(Category.name == body.categoryName).first()
    if category is None:
        category = Category(name=body.categoryName)
        db.add(category)
        db.flush()
    product = Product(sku_code=body.skuCode, name=body.name, category_id=category.id, price=body.price, status=body.status)
    db.add(product)
    db.commit()
    graph_state.mark_dirty()
    return ok({"id": product.id, "train": _start_retrain(db)})


@router.put("/products/{product_id}")
def update_product(product_id: int, body: ProductBody, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    _check_product(body)
    product = db.get(Product, product_id)
    if product is None:
        raise AppError(40410, "商品不存在", 404)
    taken = db.query(Product).filter(Product.sku_code == body.skuCode, Product.id != product.id).first()
    if taken:
        raise AppError(40012, "商品编号已存在")
    category = db.query(Category).filter(Category.name == body.categoryName).first()
    if category is None:
        category = Category(name=body.categoryName)
        db.add(category)
        db.flush()
    product.sku_code = body.skuCode
    product.name = body.name
    product.category_id = category.id
    product.price = body.price
    product.status = body.status
    db.commit()
    graph_state.mark_dirty()
    return ok({"id": product.id, "train": _start_retrain(db)})


@router.get("/behaviors")
def admin_behaviors(
    keyword: str | None = None,
    behaviorType: str | None = None,
    page: int = 1,
    pageSize: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    page, page_size = page_args(page, pageSize)
    query = (
        db.query(Behavior, Product, Category, User)
        .join(Product, Product.id == Behavior.product_id)
        .join(Category, Category.id == Product.category_id)
        .join(User, User.id == Behavior.user_id)
    )
    if behaviorType:
        query = query.filter(Behavior.behavior_type == behaviorType)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter((User.username.like(like)) | (Product.sku_code.like(like)) | (Product.name.like(like)))
    total = query.count()
    rows = query.order_by(Behavior.behavior_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for behavior, product, category, user in rows:
        item = behavior_dict(behavior, product, category.name)
        item["username"] = user.username
        items.append(item)
    return ok({"total": total, "page": page, "pageSize": page_size, "items": items})


@router.delete("/behaviors/{behavior_id}")
def delete_behavior(behavior_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    row = db.get(Behavior, behavior_id)
    if row is None:
        raise AppError(40411, "行为不存在", 404)
    db.delete(row)
    db.flush()
    rebuild_stats(db)
    graph_state.mark_dirty()
    db.commit()
    return ok()


@router.get("/behaviors/export")
def export_behaviors(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = (
        db.query(Behavior, Product, User)
        .join(Product, Product.id == Behavior.product_id)
        .join(User, User.id == Behavior.user_id)
        .order_by(Behavior.id.asc())
        .limit(200000)
        .all()
    )
    return _csv_response(
        "behaviors.csv",
        ["username", "sku_code", "behavior_type", "behavior_time"],
        [[user.username, product.sku_code, behavior.behavior_type, behavior.behavior_time.strftime("%Y-%m-%d %H:%M:%S")] for behavior, product, user in rows],
    )


@router.post("/imports/preview")
async def import_preview(
    targetTable: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    content = await file.read()
    return ok(save_preview(db, file.filename or "upload.csv", content, targetTable))


@router.get("/imports/{batch_id}/rows")
def import_rows(batch_id: int, page: int = 1, pageSize: int = 20, keyword: str = "", db: Session = Depends(get_db), _: User = Depends(require_admin)):
    page, page_size = page_args(page, pageSize)
    data = preview_rows(db, batch_id, page, page_size, keyword)
    data["page"] = page
    data["pageSize"] = page_size
    return ok(data)


@router.post("/imports/{batch_id}/commit")
def import_commit(batch_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    result = commit_batch(db, batch_id)
    if result.get("targetTable") == "product" and result.get("success", 0) > 0:
        graph_state.mark_dirty()
        result["train"] = _start_retrain(db)
    return ok(result)


@router.get("/imports/{batch_id}/errors")
def import_errors(batch_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    from app.models.tables import ImportBatch
    batch = db.get(ImportBatch, batch_id)
    if batch is None or not batch.error_report_path:
        raise AppError(40420, "没有错误报告", 404)
    path = Path(batch.error_report_path)
    if not path.exists():
        raise AppError(40420, "没有错误报告", 404)
    return StreamingResponse(path.open("rb"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=import-{batch_id}-errors.csv"})


@router.post("/data/clean")
def clean(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ok(clean_behaviors(db))


@router.get("/graph/summary")
def graph_view(page: int = 1, pageSize: int = 10, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    page, page_size = page_args(page, pageSize)
    return ok(graph_summary(db, page, page_size))


@router.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ok(overview(db))


@router.get("/stats/users/{user_id}")
def stats_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ok(user_analysis(db, user_id))


@router.get("/stats/users")
def stats_all_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ok(user_analysis(db, None))


@router.get("/stats/products")
def stats_products(page: int = 1, pageSize: int = 10, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    page, page_size = page_args(page, pageSize)
    total, items = product_stats(db, page, page_size)
    return ok({"total": total, "page": page, "pageSize": page_size, "items": items})


@router.post("/train")
def train(body: TrainBody, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    job = start_train(db, body.model_dump())
    return ok(_job_dict(job))


@router.post("/models/compare")
def compare(body: CompareBody, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    payload = body.model_dump()
    if payload.get("groups"):
        payload["groups"] = [group for group in payload["groups"]]
    job = start_compare(db, payload)
    return ok(_job_dict(job))


@router.get("/train/current")
def current_train(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    job = db.query(TrainJob).filter(TrainJob.status == "RUNNING").order_by(TrainJob.id.desc()).first()
    if job is None:
        job = db.query(TrainJob).order_by(TrainJob.id.desc()).first()
    return ok(_job_dict(job) if job else None)


@router.get("/models")
def models(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(ModelVersion).order_by(ModelVersion.id.desc()).all()
    return ok([_version_dict(row) for row in rows])


@router.put("/models/{version_id}/enable")
def enable_model(version_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    version = db.get(ModelVersion, version_id)
    if version is None:
        raise AppError(40440, "模型版本不存在", 404)
    if version.algorithm != "HETERO_SAGE" or not version.is_online_allowed:
        raise AppError(40022, "只能启用 HeteroSAGE")
    if version.status not in ("TRAINED", "DISABLED"):
        raise AppError(40022, "当前状态不能启用")
    previous = db.query(ModelVersion).filter(ModelVersion.status == "ENABLED").all()
    previous_ids = [row.id for row in previous]
    for row in previous:
        row.status = "DISABLED"
    version.status = "ENABLED"
    db.commit()
    try:
        registry.reload(db)
    except Exception as exc:
        version.status = "TRAINED"
        for row in db.query(ModelVersion).filter(ModelVersion.id.in_(previous_ids)).all():
            row.status = "ENABLED"
        db.commit()
        raise AppError(50010, f"模型加载失败：{exc}", 500)
    return ok(_version_dict(version))


@router.put("/models/{version_id}/disable")
def disable_model(version_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    version = db.get(ModelVersion, version_id)
    if version is None:
        raise AppError(40440, "模型版本不存在", 404)
    version.status = "DISABLED"
    db.commit()
    registry.reload(db)
    return ok(_version_dict(version))


@router.get("/models/{version_id}/curves")
def curves(version_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    version = db.get(ModelVersion, version_id)
    if version is None:
        raise AppError(40440, "模型版本不存在", 404)
    folder = settings.curve_dir / version.version_no
    loss = json.loads((folder / "loss.json").read_text(encoding="utf-8")) if (folder / "loss.json").exists() else []
    roc = json.loads((folder / "roc.json").read_text(encoding="utf-8")) if (folder / "roc.json").exists() else []
    return ok({"loss": loss, "roc": roc, "metrics": version.metrics or {}})


@router.get("/predictions/users/{user_id}")
def user_prediction(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise AppError(40401, "用户不存在", 404)
    rows = (
        db.query(Behavior, Product)
        .join(Product, Product.id == Behavior.product_id)
        .filter(Behavior.user_id == user_id)
        .order_by(Behavior.behavior_time.desc())
        .limit(50)
        .all()
    )
    prediction = predict_for_user(db, user_id, "ADMIN_VIEW")
    return ok({
        "user": user_dict(user),
        "behaviors": [
            {
                "behaviorTime": behavior.behavior_time.strftime("%Y-%m-%d %H:%M:%S"),
                "productName": product.name,
                "behaviorType": behavior.behavior_type,
                "behaviorLabel": BEHAVIOR_LABEL.get(behavior.behavior_type, behavior.behavior_type),
            }
            for behavior, product in rows
        ],
        "prediction": prediction,
    })


@router.post("/predictions/batch")
def predictions_batch(body: BatchBody, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user_ids = list(body.userIds)
    if body.keyword:
        like = f"%{body.keyword.strip()}%"
        user_ids.extend([row.id for row in db.query(User).filter(User.username.like(like)).limit(500).all()])
    return ok(batch_predict(db, user_ids))


@router.get("/predictions")
def admin_predictions(page: int = 1, pageSize: int = 10, username: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    page, page_size = page_args(page, pageSize)
    query = db.query(Prediction, User).join(User, User.id == Prediction.user_id)
    if username:
        query = query.filter(User.username.like(f"%{username.strip()}%"))
    total = query.count()
    rows = query.order_by(Prediction.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": [_prediction_payload(db, prediction) for prediction, _user in rows],
    })


@router.get("/predictions/export")
def export_predictions(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    latest = (
        db.query(Prediction.batch_key)
        .filter(Prediction.batch_key.isnot(None))
        .order_by(Prediction.id.desc())
        .first()
    )
    if latest is None:
        raise AppError(40041, "还没有批量预测结果")
    batch_key = latest[0]
    count = (
        db.query(func.count(PredictionItem.id))
        .join(Prediction, Prediction.id == PredictionItem.prediction_id)
        .filter(Prediction.batch_key == batch_key)
        .scalar()
        or 0
    )
    if count > 5000:
        raise AppError(40041, "单次最多导出 5000 行")
    rows = (
        db.query(Prediction, PredictionItem, Product, User)
        .join(PredictionItem, PredictionItem.prediction_id == Prediction.id)
        .join(Product, Product.id == PredictionItem.product_id)
        .join(User, User.id == Prediction.user_id)
        .filter(Prediction.batch_key == batch_key)
        .order_by(Prediction.id.asc(), PredictionItem.rank_no.asc())
        .all()
    )
    return _csv_response(
        "predictions.csv",
        ["username", "product_name", "probability", "source", "reason", "status_text", "created_at"],
        [[
            user.username,
            product.name,
            float(item.probability),
            prediction.result_source,
            item.reason,
            prediction.status_text,
            prediction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ] for prediction, item, product, user in rows],
    )


@router.get("/predictions/analysis")
def analysis(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ok(prediction_analysis(db))


def _start_retrain(db: Session) -> dict:
    try:
        job = start_train(db, {
            "algorithm": "HETERO_SAGE",
            "learningRate": 0.001,
            "batchSize": 1024,
            "epochs": 30,
        })
        return {"started": True, "jobId": job.id, "status": job.status}
    except AppError as exc:
        return {"started": False, "message": exc.message}


def _job_dict(job: TrainJob | None) -> dict | None:
    if job is None:
        return None
    return {
        "id": job.id,
        "algorithm": job.algorithm,
        "status": job.status,
        "hyperParams": job.hyper_params,
        "logText": job.log_text or "",
        "startedAt": job.started_at.strftime("%Y-%m-%d %H:%M:%S") if job.started_at else "",
        "finishedAt": job.finished_at.strftime("%Y-%m-%d %H:%M:%S") if job.finished_at else "",
    }


def _version_dict(row: ModelVersion) -> dict:
    return {
        "id": row.id,
        "algorithm": row.algorithm,
        "versionNo": row.version_no,
        "hyperParams": row.hyper_params,
        "metrics": row.metrics,
        "status": row.status,
        "onlineAllowed": bool(row.is_online_allowed),
        "createdAt": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
    }


def _csv_response(filename: str, header: list[str], rows: list[list]):
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    data = buffer.getvalue().encode("utf-8")
    return StreamingResponse(iter([data]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})
