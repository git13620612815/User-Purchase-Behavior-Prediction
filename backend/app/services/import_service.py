from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.constants import HEADER_MAP, MIN_TIME, TIME_FORMAT
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import hash_password
from app.graph.state import graph_state
from app.models.tables import Behavior, Category, ImportBatch, Product, User
from app.services.behavior_service import rebuild_stats

IMPORT_PASSWORD = "Import12345"


def save_preview(db: Session, filename: str, content: bytes, target_table: str) -> dict:
    if target_table not in HEADER_MAP:
        raise AppError(40020, "导入类型不正确")
    if not filename.lower().endswith(".csv"):
        raise AppError(40020, "只接受 CSV 文件")
    if len(content) > 50 * 1024 * 1024:
        raise AppError(40020, "文件不能超过 50MB")
    batch = ImportBatch(file_name=filename, file_path="", target_table=target_table, status="PREVIEW")
    db.add(batch)
    db.flush()
    path = settings.import_dir / f"{batch.id}.csv"
    path.write_bytes(content)
    batch.file_path = str(path)
    try:
        frame = _read_csv(path)
    except UnicodeError:
        db.rollback()
        path.unlink(missing_ok=True)
        raise AppError(40021, "请使用 UTF-8 编码的 CSV")
    except Exception as exc:
        db.rollback()
        path.unlink(missing_ok=True)
        raise AppError(40021, f"无法读取 CSV：{exc}")
    expected = HEADER_MAP[target_table]
    if list(frame.columns) != expected:
        db.rollback()
        path.unlink(missing_ok=True)
        raise AppError(40021, "表头不正确")
    preview = _page_frame(frame, 1, 20, "")
    batch.total_rows = int(len(frame))
    db.commit()
    return {"batchId": batch.id, "total": batch.total_rows, "columns": expected, "rows": preview["items"]}


def preview_rows(db: Session, batch_id: int, page: int, page_size: int, keyword: str) -> dict:
    batch = _preview_batch(db, batch_id)
    frame = _read_csv(Path(batch.file_path))
    rows = _page_frame(frame, page, page_size, keyword)
    return {"batchId": batch.id, "total": rows["total"], "columns": list(frame.columns), "rows": rows["items"]}


def commit_batch(db: Session, batch_id: int) -> dict:
    batch = _preview_batch(db, batch_id)
    frame = _read_csv(Path(batch.file_path))
    if list(frame.columns) != HEADER_MAP[batch.target_table]:
        raise AppError(40021, "表头不正确")
    errors = []
    success = 0
    duplicate = 0
    if batch.target_table == "user":
        success, duplicate, errors = _commit_users(db, frame)
    elif batch.target_table == "product":
        success, duplicate, errors = _commit_products(db, frame)
    else:
        success, duplicate, errors = _commit_behaviors(db, frame)
        rebuild_stats(db)
        graph_state.mark_dirty()
    report = None
    if errors:
        report_path = settings.import_dir / f"{batch.id}_errors.csv"
        pd.DataFrame(errors).to_csv(report_path, index=False, encoding="utf-8-sig")
        report = str(report_path)
    batch.success_rows = success
    batch.rejected_rows = len(errors)
    batch.duplicate_rows = duplicate
    batch.total_rows = int(len(frame))
    batch.status = "COMMITTED"
    batch.error_report_path = report
    db.commit()
    return {
        "batchId": batch.id,
        "total": batch.total_rows,
        "success": success,
        "rejected": len(errors),
        "duplicate": duplicate,
        "targetTable": batch.target_table,
    }


def clean_behaviors(db: Session) -> dict:
    now = datetime.now()
    illegal = db.query(Behavior).filter((Behavior.behavior_time < MIN_TIME) | (Behavior.behavior_time > now)).delete(synchronize_session=False)
    dup_result = db.execute(text(
        """
        DELETE b1 FROM behavior b1
        INNER JOIN behavior b2
          ON b1.user_id = b2.user_id
         AND b1.product_id = b2.product_id
         AND b1.behavior_type = b2.behavior_type
         AND b1.behavior_time = b2.behavior_time
         AND b1.id > b2.id
        """
    ))
    rebuild_stats(db)
    graph_state.mark_dirty()
    db.commit()
    return {"deletedIllegal": int(illegal or 0), "deletedDuplicate": int(dup_result.rowcount or 0)}


def _preview_batch(db: Session, batch_id: int) -> ImportBatch:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise AppError(40420, "导入批次不存在", 404)
    if batch.status != "PREVIEW":
        raise AppError(40020, "该批次已处理")
    return batch


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def _page_frame(frame: pd.DataFrame, page: int, page_size: int, keyword: str) -> dict:
    data = frame
    if keyword:
        mask = data.apply(lambda column: column.str.contains(keyword, case=False, na=False)).any(axis=1)
        data = data[mask]
    total = int(len(data))
    start = (page - 1) * page_size
    page_df = data.iloc[start:start + page_size]
    return {"total": total, "items": page_df.to_dict(orient="records")}


def _parse_time(value: str) -> datetime | None:
    text_value = (value or "").strip()
    try:
        return datetime.strptime(text_value, TIME_FORMAT)
    except ValueError:
        return None


def _legal_time(value: datetime | None) -> str | None:
    if value is None:
        return "时间无法解析"
    if value < MIN_TIME:
        return "时间早于 2000-01-01"
    if value > datetime.now():
        return "时间晚于当前时间"
    return None


def _commit_users(db: Session, frame: pd.DataFrame):
    success = duplicate = 0
    errors = []
    password_hash = hash_password(IMPORT_PASSWORD)
    existing = {name for (name,) in db.query(User.username).all()}
    for offset, row in enumerate(frame.itertuples(index=False), start=2):
        username = row.username.strip()
        if username in existing:
            duplicate += 1
            continue
        if not username:
            errors.append({"row": offset, "reason": "用户名为空", "raw": username})
            continue
        gender = _gender(row.gender)
        if gender is None:
            errors.append({"row": offset, "reason": "性别不合法", "raw": row.gender})
            continue
        age = None
        if row.age.strip():
            try:
                age = int(row.age)
            except ValueError:
                errors.append({"row": offset, "reason": "年龄不合法", "raw": row.age})
                continue
            if age < 0 or age > 120:
                errors.append({"row": offset, "reason": "年龄不合法", "raw": row.age})
                continue
        when = _parse_time(row.register_time) if row.register_time.strip() else datetime.now()
        problem = _legal_time(when) if row.register_time.strip() else None
        if problem:
            errors.append({"row": offset, "reason": problem, "raw": row.register_time})
            continue
        db.add(User(
            username=username,
            password_hash=password_hash,
            nickname=row.nickname.strip() or username,
            gender=gender,
            age=age,
            phone=row.phone.strip() or None,
            email=row.email.strip() or None,
            role="USER",
            status="ENABLED",
            created_at=when,
        ))
        existing.add(username)
        success += 1
    return success, duplicate, errors


def _commit_products(db: Session, frame: pd.DataFrame):
    success = duplicate = 0
    errors = []
    existing = {sku for (sku,) in db.query(Product.sku_code).all()}
    categories = {row.name: row for row in db.query(Category).all()}
    for offset, row in enumerate(frame.itertuples(index=False), start=2):
        sku = row.sku_code.strip()
        name = row.name.strip()
        category_name = row.category_name.strip()
        if not sku or not name or not category_name:
            errors.append({"row": offset, "reason": "商品编号、名称或类目为空", "raw": sku})
            continue
        if sku in existing:
            duplicate += 1
            continue
        try:
            price = float(row.price)
        except ValueError:
            errors.append({"row": offset, "reason": "价格不合法", "raw": row.price})
            continue
        if price < 0:
            errors.append({"row": offset, "reason": "价格不合法", "raw": row.price})
            continue
        category = categories.get(category_name)
        if category is None:
            category = Category(name=category_name)
            db.add(category)
            db.flush()
            categories[category_name] = category
        db.add(Product(sku_code=sku, name=name, category_id=category.id, price=price, status="ON"))
        existing.add(sku)
        success += 1
    return success, duplicate, errors


def _commit_behaviors(db: Session, frame: pd.DataFrame):
    success = duplicate = 0
    errors = []
    users = {row.username: row.id for row in db.query(User).all()}
    products = {row.sku_code: row.id for row in db.query(Product).all()}
    existing = {
        (row.user_id, row.product_id, row.behavior_type, row.behavior_time.replace(microsecond=0))
        for row in db.query(Behavior).all()
    }
    allowed = {"browse", "favorite", "cart", "purchase"}
    for offset, row in enumerate(frame.itertuples(index=False), start=2):
        username = row.username.strip()
        sku = row.sku_code.strip()
        behavior_type = row.behavior_type.strip()
        if behavior_type not in allowed:
            errors.append({"row": offset, "reason": "非法行为", "raw": behavior_type})
            continue
        user_id = users.get(username)
        product_id = products.get(sku)
        if user_id is None or product_id is None:
            errors.append({"row": offset, "reason": "非法编号", "raw": f"{username},{sku}"})
            continue
        when = _parse_time(row.behavior_time)
        problem = _legal_time(when)
        if problem:
            errors.append({"row": offset, "reason": problem, "raw": row.behavior_time})
            continue
        key = (user_id, product_id, behavior_type, when)
        if key in existing:
            duplicate += 1
            continue
        db.add(Behavior(user_id=user_id, product_id=product_id, behavior_type=behavior_type, behavior_time=when, source="IMPORT"))
        existing.add(key)
        success += 1
    return success, duplicate, errors


def _gender(value: str) -> str | None:
    text_value = (value or "").strip()
    mapping = {"": "未知", "未知": "未知", "男": "男", "女": "女", "M": "男", "F": "女", "U": "未知"}
    return mapping.get(text_value)
