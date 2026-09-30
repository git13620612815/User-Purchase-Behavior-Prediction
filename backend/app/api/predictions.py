from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.common import ok, page_args
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models.tables import Prediction, User
from app.services.predict_service import _prediction_payload, predict_for_user

router = APIRouter(prefix="/predictions", tags=["predictions"])


class PredictBody(BaseModel):
    productId: int | None = None


@router.post("")
def create_prediction(
    body: PredictBody | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product_id = body.productId if body else None
    return ok(predict_for_user(db, user.id, "USER_VIEW", focus_product_id=product_id))


@router.get("")
def list_predictions(
    page: int = 1,
    pageSize: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page, page_size = page_args(page, pageSize)
    query = db.query(Prediction).filter(Prediction.user_id == user.id)
    total = query.count()
    rows = query.order_by(Prediction.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": [_prediction_payload(db, row) for row in rows],
    })


@router.get("/{prediction_id}")
def prediction_detail(
    prediction_id: int,
    categoryId: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(Prediction, prediction_id)
    if row is None or (user.role != "ADMIN" and row.user_id != user.id):
        raise AppError(40430, "预测记录不存在", 404)
    payload = _prediction_payload(db, row)
    if categoryId:
        payload["items"] = [item for item in payload["items"] if item["categoryId"] == categoryId]
    return ok(payload)
