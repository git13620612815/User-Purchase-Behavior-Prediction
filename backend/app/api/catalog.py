from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.common import ok, page_args
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models.tables import Category, Product, User
from app.services.behavior_service import record_behavior

router = APIRouter(tags=["catalog"])


def product_dict(product: Product, category_name: str) -> dict:
    return {
        "id": product.id,
        "skuCode": product.sku_code,
        "name": product.name,
        "categoryId": product.category_id,
        "categoryName": category_name,
        "price": float(product.price or 0),
        "status": product.status,
    }


@router.get("/categories")
def categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Category).order_by(Category.id.asc()).all()
    return ok([{"id": row.id, "name": row.name} for row in rows])


@router.get("/products")
def products(
    categoryId: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    pageSize: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    page, page_size = page_args(page, pageSize)
    query = db.query(Product, Category).join(Category, Category.id == Product.category_id).filter(Product.status == "ON")
    if categoryId:
        query = query.filter(Product.category_id == categoryId)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter((Product.name.like(like)) | (Product.sku_code.like(like)))
    total = query.count()
    rows = query.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": [product_dict(product, category.name) for product, category in rows],
    })


@router.get("/products/{product_id}")
def product_detail(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(Product, Category).join(Category, Category.id == Product.category_id).filter(Product.id == product_id).first()
    if row is None or row[0].status != "ON":
        raise AppError(40410, "商品不存在", 404)
    product, category = row
    record_behavior(db, user.id, product.id, "browse")
    return ok(product_dict(product, category.name))
