import math
import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import BEHAVIOR_LABEL, SOURCE_LABEL
from app.core.errors import AppError
from app.graph.infer import score_user
from app.graph.registry import registry
from app.models.tables import Behavior, Category, Prediction, PredictionItem, Product, User
from app.services.stats_service import hot_products


def predict_for_user(db: Session, user_id: int, trigger: str, batch_key: str | None = None, focus_product_id: int | None = None) -> dict:
    started = datetime.now()
    behavior_count = db.query(func.count(Behavior.id)).filter(Behavior.user_id == user_id).scalar() or 0
    version_id = None
    focus_probability = None
    if behavior_count == 0:
        source = "POPULAR"
        status_text = "行为不足"
        raw_items = _popular_raw(db)
    else:
        model, _scalers, _meta, version_id = registry.snapshot()
        if model is None or version_id is None:
            source = "POPULAR"
            status_text = "当前没有启用的预测模型"
            raw_items = _popular_raw(db)
            version_id = None
        else:
            source = "GNN"
            status_text = ""
            raw_items, focus_probability = score_user(db, user_id, focus_product_id)
            if not raw_items:
                source = "POPULAR"
                status_text = "没有可预测的未购买商品"
                raw_items = _popular_raw(db)
                version_id = None
                focus_probability = None
    items = _decorate(db, user_id, raw_items, source)
    elapsed = int((datetime.now() - started).total_seconds() * 1000)
    prediction = Prediction(
        user_id=user_id,
        model_version_id=version_id,
        result_source=source,
        status_text=status_text,
        trigger_type=trigger,
        elapsed_ms=elapsed,
        batch_key=batch_key,
        created_at=datetime.now(),
    )
    db.add(prediction)
    db.flush()
    for item in items:
        db.add(PredictionItem(
            prediction_id=prediction.id,
            product_id=item["productId"],
            rank_no=item["rankNo"],
            probability=item["probability"],
            reason=item["reason"],
            category_id=item["categoryId"],
        ))
    db.commit()
    db.refresh(prediction)
    payload = _prediction_payload(db, prediction, items)
    purchased = False
    if focus_product_id and focus_probability is None:
        purchased = (
            db.query(Behavior.id)
            .filter(
                Behavior.user_id == user_id,
                Behavior.product_id == focus_product_id,
                Behavior.behavior_type == "purchase",
            )
            .first()
            is not None
        )
    payload["focusProductId"] = focus_product_id
    payload["focusProbability"] = focus_probability
    payload["focusPurchased"] = purchased
    return payload


def _popular_raw(db: Session) -> list[dict]:
    rows = hot_products(db, 10)
    total = sum(row["purchaseCount"] for row in rows) or 0
    result = []
    if not rows:
        products = db.query(Product).filter(Product.status == "ON").order_by(Product.id.asc()).limit(10).all()
        share = round(1 / len(products), 4) if products else 0
        return [{"productId": product.id, "probability": share, "purchaseCount": 0} for product in products]
    for index, row in enumerate(rows, start=1):
        if total:
            probability = round(row["purchaseCount"] / total, 4)
        else:
            probability = round(1 / len(rows), 4)
        result.append({**row, "probability": probability, "rankHint": index})
    return result


def _decorate(db: Session, user_id: int, raw_items: list[dict], source: str) -> list[dict]:
    if not raw_items:
        return []
    product_ids = [item["productId"] for item in raw_items]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {product.id: product for product in products}
    categories = db.query(Category).all()
    category_map = {category.id: category.name for category in categories}
    behaviors = db.query(Behavior).filter(Behavior.user_id == user_id).all()
    product_category = {product.id: product.category_id for product in db.query(Product).all()}
    decorated = []
    for index, item in enumerate(raw_items, start=1):
        product = product_map.get(item["productId"])
        if product is None:
            continue
        if source == "GNN":
            reason = _gnn_reason(behaviors, product, product_category, category_map)
        else:
            rank_no = item.get("rankHint", index)
            reason = f"全站购买量第 {rank_no} 名"
        decorated.append({
            "productId": product.id,
            "productName": product.name,
            "skuCode": product.sku_code,
            "price": float(product.price or 0),
            "categoryId": product.category_id,
            "categoryName": category_map.get(product.category_id, ""),
            "probability": float(item["probability"]),
            "source": SOURCE_LABEL[source],
            "reason": reason,
            "rankNo": len(decorated) + 1,
        })
    return decorated


def _gnn_reason(behaviors: list[Behavior], product: Product, product_category: dict, category_map: dict) -> str:
    strongest = 0
    for row in behaviors:
        if row.product_id != product.id:
            continue
        if row.behavior_type == "cart":
            strongest = max(strongest, 3)
        elif row.behavior_type == "favorite":
            strongest = max(strongest, 2)
    if strongest >= 3:
        return "已加购该商品"
    if strongest >= 2:
        return "已收藏该商品"
    purchased_same = False
    soft_same = False
    for row in behaviors:
        if product_category.get(row.product_id) != product.category_id:
            continue
        if row.behavior_type == "purchase":
            purchased_same = True
        if row.behavior_type in ("browse", "favorite"):
            soft_same = True
    name = category_map.get(product.category_id, "该类目")
    if purchased_same:
        return f"您购买过同类目「{name}」"
    if soft_same:
        return f"您在「{name}」有浏览或收藏"
    return "与您最近交互商品属于相近类目"


def _prediction_payload(db: Session, prediction: Prediction, items: list[dict] | None = None) -> dict:
    if items is None:
        stored = (
            db.query(PredictionItem, Product, Category)
            .join(Product, Product.id == PredictionItem.product_id)
            .join(Category, Category.id == Product.category_id)
            .filter(PredictionItem.prediction_id == prediction.id)
            .order_by(PredictionItem.rank_no.asc())
            .all()
        )
        items = [
            {
                "productId": product.id,
                "productName": product.name,
                "skuCode": product.sku_code,
                "price": float(product.price or 0),
                "categoryId": category.id,
                "categoryName": category.name,
                "probability": float(item.probability),
                "source": SOURCE_LABEL.get(prediction.result_source, prediction.result_source),
                "reason": item.reason,
                "rankNo": item.rank_no,
            }
            for item, product, category in stored
        ]
    user = db.get(User, prediction.user_id)
    return {
        "predictionId": prediction.id,
        "userId": prediction.user_id,
        "username": user.username if user else "",
        "resultSource": prediction.result_source,
        "sourceLabel": SOURCE_LABEL.get(prediction.result_source, prediction.result_source),
        "statusText": prediction.status_text or "",
        "triggerType": prediction.trigger_type,
        "elapsedMs": prediction.elapsed_ms,
        "batchKey": prediction.batch_key,
        "createdAt": prediction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
    }


def batch_predict(db: Session, user_ids: list[int]) -> dict:
    unique_ids = []
    seen = set()
    for user_id in user_ids:
        if user_id not in seen:
            seen.add(user_id)
            unique_ids.append(user_id)
    if not unique_ids:
        raise AppError(40040, "请选择用户")
    if len(unique_ids) > 500:
        raise AppError(40040, "单次批量最多 500 名用户")
    batch_key = uuid.uuid4().hex
    count = 0
    for user_id in unique_ids:
        user = db.get(User, user_id)
        if user is None:
            continue
        predict_for_user(db, user_id, "BATCH", batch_key)
        count += 1
    return {"batchKey": batch_key, "count": count}


def prediction_analysis(db: Session) -> dict:
    predictions = db.query(Prediction).all()
    items = db.query(PredictionItem).all()
    buckets = [{"start": round(i / 10, 1), "end": round((i + 1) / 10, 1), "count": 0} for i in range(10)]
    for item in items:
        index = min(9, max(0, int(math.floor(float(item.probability) * 10))))
        if float(item.probability) >= 1:
            index = 9
        buckets[index]["count"] += 1
    high_users = set()
    for item in items:
        if float(item.probability) >= 0.7:
            prediction = db.get(Prediction, item.prediction_id)
            if prediction:
                high_users.add(prediction.user_id)
    product_counter: dict[int, int] = {}
    for item in items:
        product_counter[item.product_id] = product_counter.get(item.product_id, 0) + 1
    top_ids = sorted(product_counter, key=lambda key: product_counter[key], reverse=True)[:20]
    products = db.query(Product).filter(Product.id.in_(top_ids)).all() if top_ids else []
    product_map = {product.id: product for product in products}
    total = len(predictions)
    gnn_count = sum(1 for row in predictions if row.result_source == "GNN")
    fallback_count = sum(1 for row in predictions if row.result_source == "POPULAR")
    avg_elapsed = round(sum(row.elapsed_ms for row in predictions) / total, 2) if total else 0
    return {
        "distribution": buckets,
        "highProbabilityUsers": len(high_users),
        "highProbabilityThreshold": 0.7,
        "potentialProducts": [
            {"productId": product_id, "name": product_map[product_id].name if product_id in product_map else "", "count": product_counter[product_id]}
            for product_id in top_ids
        ],
        "predictionCount": total,
        "successCount": gnn_count,
        "successRate": round(gnn_count / total, 4) if total else 0,
        "fallbackCount": fallback_count,
        "avgElapsedMs": avg_elapsed,
    }


def behavior_label(behavior_type: str) -> str:
    return BEHAVIOR_LABEL.get(behavior_type, behavior_type)
