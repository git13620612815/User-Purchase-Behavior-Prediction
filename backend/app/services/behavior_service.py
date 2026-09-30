from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import BEHAVIOR_LABEL, BEHAVIOR_WEIGHT
from app.core.errors import AppError
from app.core.redis import redis_client
from app.graph.state import graph_state
from app.models.tables import Behavior, Product, StatDaily

TYPES = tuple(BEHAVIOR_WEIGHT)


def record_behavior(db: Session, user_id: int, product_id: int, behavior_type: str, source: str = "FRONT") -> Behavior | None:
    if behavior_type not in TYPES:
        raise AppError(40010, "行为类型不合法")
    product = db.get(Product, product_id)
    if product is None or product.status != "ON":
        raise AppError(40410, "商品不存在", 404)
    now = datetime.now().replace(microsecond=0)
    if behavior_type == "browse":
        cutoff = now - timedelta(minutes=30)
        exists = (
            db.query(Behavior)
            .filter(
                Behavior.user_id == user_id,
                Behavior.product_id == product_id,
                Behavior.behavior_type == "browse",
                Behavior.behavior_time >= cutoff,
            )
            .first()
        )
        if exists:
            return exists
    for offset in range(6):
        when = now + timedelta(seconds=offset)
        row = Behavior(
            user_id=user_id,
            product_id=product_id,
            behavior_type=behavior_type,
            behavior_time=when,
            source=source,
        )
        db.add(row)
        try:
            db.flush()
            _bump_stat(db, user_id, when, behavior_type)
            db.commit()
            graph_state.mark_dirty()
            if behavior_type == "purchase":
                redis_client.delete("hot:products")
            return row
        except IntegrityError:
            db.rollback()
    raise AppError(40011, "行为写入失败")


def _bump_stat(db: Session, user_id: int, when: datetime, behavior_type: str) -> None:
    day = when.date()
    row = db.query(StatDaily).filter(StatDaily.stat_date == day, StatDaily.behavior_type == behavior_type).first()
    first = (
        db.query(func.count(Behavior.id))
        .filter(
            Behavior.user_id == user_id,
            Behavior.behavior_type == behavior_type,
            func.date(Behavior.behavior_time) == day,
        )
        .scalar()
        or 0
    )
    if row is None:
        row = StatDaily(
            stat_date=day,
            behavior_type=behavior_type,
            user_count=1,
            behavior_count=1,
            purchase_count=1 if behavior_type == "purchase" else 0,
        )
        db.add(row)
        return
    row.behavior_count += 1
    if first <= 1:
        row.user_count += 1
    if behavior_type == "purchase":
        row.purchase_count += 1


def rebuild_stats(db: Session) -> None:
    db.query(StatDaily).delete()
    rows = (
        db.query(
            func.date(Behavior.behavior_time),
            Behavior.behavior_type,
            func.count(Behavior.id),
            func.count(func.distinct(Behavior.user_id)),
        )
        .group_by(func.date(Behavior.behavior_time), Behavior.behavior_type)
        .all()
    )
    for stat_date, behavior_type, count, users in rows:
        db.add(
            StatDaily(
                stat_date=stat_date,
                behavior_type=behavior_type,
                behavior_count=int(count),
                user_count=int(users),
                purchase_count=int(count) if behavior_type == "purchase" else 0,
            )
        )


def behavior_dict(row: Behavior, product: Product | None, category_name: str | None = None) -> dict:
    return {
        "id": row.id,
        "userId": row.user_id,
        "productId": row.product_id,
        "productName": product.name if product else "",
        "skuCode": product.sku_code if product else "",
        "categoryName": category_name or "",
        "behaviorType": row.behavior_type,
        "behaviorLabel": BEHAVIOR_LABEL.get(row.behavior_type, row.behavior_type),
        "behaviorTime": row.behavior_time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": row.source,
    }
