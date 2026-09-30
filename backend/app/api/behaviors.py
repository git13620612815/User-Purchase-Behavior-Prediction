from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.common import ok, page_args
from app.constants import BEHAVIOR_LABEL
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models.tables import Behavior, Category, Product, User
from app.services.behavior_service import behavior_dict, record_behavior

router = APIRouter(prefix="/behaviors", tags=["behaviors"])


class BehaviorBody(BaseModel):
    productId: int
    behaviorType: str


@router.post("")
def create_behavior(body: BehaviorBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.behaviorType not in ("favorite", "cart", "purchase"):
        raise AppError(40010, "行为类型不合法")
    row = record_behavior(db, user.id, body.productId, body.behaviorType)
    product = db.get(Product, row.product_id)
    category = db.get(Category, product.category_id) if product else None
    return ok(behavior_dict(row, product, category.name if category else ""))


@router.get("/mine")
def mine(
    behaviorType: str | None = None,
    page: int = 1,
    pageSize: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page, page_size = page_args(page, pageSize)
    query = (
        db.query(Behavior, Product, Category)
        .join(Product, Product.id == Behavior.product_id)
        .join(Category, Category.id == Product.category_id)
        .filter(Behavior.user_id == user.id)
    )
    if behaviorType:
        query = query.filter(Behavior.behavior_type == behaviorType)
    total = query.count()
    rows = query.order_by(Behavior.behavior_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    counts = dict(
        db.query(Behavior.behavior_type, func.count(Behavior.id))
        .filter(Behavior.user_id == user.id)
        .group_by(Behavior.behavior_type)
        .all()
    )
    return ok({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "counts": {key: int(counts.get(key, 0)) for key in BEHAVIOR_LABEL},
        "items": [behavior_dict(behavior, product, category.name) for behavior, product, category in rows],
    })
