import json

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.constants import BEHAVIOR_LABEL
from app.core.redis import redis_client
from app.models.tables import Behavior, Category, Product

WEEKDAY = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
FUNNEL_ORDER = ["browse", "favorite", "cart", "purchase"]


def hot_products(db: Session, limit: int = 10) -> list[dict]:
    cache_key = "hot:products"
    cached = redis_client.get(cache_key)
    rows = json.loads(cached) if cached else None
    if rows is None:
        purchase = func.sum(case((Behavior.behavior_type == "purchase", 1), else_=0))
        cart = func.sum(case((Behavior.behavior_type == "cart", 1), else_=0))
        queried = (
            db.query(Behavior.product_id, purchase.label("purchase_count"), cart.label("cart_count"))
            .group_by(Behavior.product_id)
            .order_by(purchase.desc(), cart.desc())
            .limit(20)
            .all()
        )
        rows = [
            {"productId": int(item.product_id), "purchaseCount": int(item.purchase_count or 0), "cartCount": int(item.cart_count or 0)}
            for item in queried
        ]
        redis_client.setex(cache_key, 600, json.dumps(rows))
    return rows[:limit]


def overview(db: Session) -> dict:
    active = (
        db.query(func.date(Behavior.behavior_time).label("d"), func.count(func.distinct(Behavior.user_id)))
        .group_by("d")
        .order_by("d")
        .all()
    )
    purchase_trend = (
        db.query(func.date(Behavior.behavior_time).label("d"), func.count(Behavior.id))
        .filter(Behavior.behavior_type == "purchase")
        .group_by("d")
        .order_by("d")
        .all()
    )
    counts = dict(
        db.query(Behavior.behavior_type, func.count(Behavior.id)).group_by(Behavior.behavior_type).all()
    )
    funnel = [
        {"type": key, "label": BEHAVIOR_LABEL[key], "count": int(counts.get(key, 0))}
        for key in FUNNEL_ORDER
    ]
    categories = (
        db.query(Category.name, func.count(Behavior.id))
        .join(Product, Product.category_id == Category.id)
        .join(Behavior, Behavior.product_id == Product.id)
        .filter(Behavior.behavior_type == "purchase")
        .group_by(Category.name)
        .order_by(func.count(Behavior.id).desc())
        .all()
    )
    heat_rows = (
        db.query(func.weekday(Behavior.behavior_time), func.hour(Behavior.behavior_time), func.count(Behavior.id))
        .filter(Behavior.behavior_type == "purchase")
        .group_by(func.weekday(Behavior.behavior_time), func.hour(Behavior.behavior_time))
        .all()
    )
    top = _top_products(db, 10)
    return {
        "activeTrend": [{"date": str(day), "userCount": int(count)} for day, count in active],
        "purchaseTrend": [{"date": str(day), "count": int(count)} for day, count in purchase_trend],
        "funnel": funnel,
        "categoryDistribution": [{"name": name, "count": int(count)} for name, count in categories],
        "heatmap": [
            {"weekday": int(day), "weekdayLabel": WEEKDAY[int(day)] if day is not None and 0 <= int(day) < 7 else str(day), "hour": int(hour), "count": int(count)}
            for day, hour, count in heat_rows
        ],
        "topProducts": top,
    }


def user_analysis(db: Session, user_id: int | None = None) -> dict:
    query = db.query(Behavior)
    if user_id is not None:
        query = query.filter(Behavior.user_id == user_id)
    counts = dict(
        query.with_entities(Behavior.behavior_type, func.count(Behavior.id)).group_by(Behavior.behavior_type).all()
    )
    active_days = query.with_entities(func.count(func.distinct(func.date(Behavior.behavior_time)))).scalar() or 0
    purchase_count = int(counts.get("purchase", 0))
    browse_count = int(counts.get("browse", 0))
    hours = (
        query.filter(Behavior.behavior_type == "purchase")
        .with_entities(func.hour(Behavior.behavior_time), func.count(Behavior.id))
        .group_by(func.hour(Behavior.behavior_time))
        .all()
    )
    weeks = (
        query.filter(Behavior.behavior_type == "purchase")
        .with_entities(func.weekday(Behavior.behavior_time), func.count(Behavior.id))
        .group_by(func.weekday(Behavior.behavior_time))
        .all()
    )
    cat_query = (
        db.query(Category.name, func.count(Behavior.id))
        .join(Product, Product.category_id == Category.id)
        .join(Behavior, Behavior.product_id == Product.id)
        .filter(Behavior.behavior_type == "purchase")
    )
    if user_id is not None:
        cat_query = cat_query.filter(Behavior.user_id == user_id)
    categories = cat_query.group_by(Category.name).order_by(func.count(Behavior.id).desc()).all()
    typed = {key: int(counts.get(key, 0)) for key in FUNNEL_ORDER}
    total = sum(typed.values())
    return {
        "activeDays": int(active_days),
        "counts": typed,
        "ratios": {key: round(value / total, 4) if total else 0 for key, value in typed.items()},
        "purchaseFrequency": round(purchase_count / active_days, 4) if active_days else 0,
        "purchaseConversion": None if browse_count == 0 else round(purchase_count / browse_count, 4),
        "purchaseConversionText": None if browse_count else "无浏览",
        "hourDistribution": [{"hour": int(hour), "count": int(count)} for hour, count in hours],
        "weekdayDistribution": [
            {"weekday": int(day), "weekdayLabel": WEEKDAY[int(day)] if 0 <= int(day) < 7 else str(day), "count": int(count)}
            for day, count in weeks
        ],
        "categoryStats": [{"name": name, "count": int(count)} for name, count in categories],
    }


def product_stats(db: Session, page: int, page_size: int) -> tuple[int, list[dict]]:
    purchase = func.sum(case((Behavior.behavior_type == "purchase", 1), else_=0))
    browse = func.sum(case((Behavior.behavior_type == "browse", 1), else_=0))
    favorite = func.sum(case((Behavior.behavior_type == "favorite", 1), else_=0))
    cart = func.sum(case((Behavior.behavior_type == "cart", 1), else_=0))
    grouped = (
        db.query(
            Product.id,
            Product.name,
            Product.sku_code,
            Category.name.label("category_name"),
            browse.label("browse_count"),
            favorite.label("favorite_count"),
            cart.label("cart_count"),
            purchase.label("purchase_count"),
        )
        .join(Category, Category.id == Product.category_id)
        .outerjoin(Behavior, Behavior.product_id == Product.id)
        .group_by(Product.id, Product.name, Product.sku_code, Category.name)
        .order_by(purchase.desc(), cart.desc())
    )
    total = grouped.count()
    rows = grouped.offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for row in rows:
        browse_count = int(row.browse_count or 0)
        purchase_count = int(row.purchase_count or 0)
        items.append({
            "productId": row.id,
            "name": row.name,
            "skuCode": row.sku_code,
            "categoryName": row.category_name,
            "browseCount": browse_count,
            "favoriteCount": int(row.favorite_count or 0),
            "cartCount": int(row.cart_count or 0),
            "purchaseCount": purchase_count,
            "conversion": None if browse_count == 0 else round(purchase_count / browse_count, 4),
        })
    return total, items


def _top_products(db: Session, limit: int) -> list[dict]:
    purchase = func.sum(case((Behavior.behavior_type == "purchase", 1), else_=0))
    rows = (
        db.query(Product.id, Product.name, Category.name, purchase.label("purchase_count"))
        .join(Category, Category.id == Product.category_id)
        .join(Behavior, Behavior.product_id == Product.id)
        .group_by(Product.id, Product.name, Category.name)
        .order_by(purchase.desc())
        .limit(limit)
        .all()
    )
    return [
        {"productId": row.id, "name": row.name, "categoryName": row[2], "purchaseCount": int(row.purchase_count or 0)}
        for row in rows
    ]
