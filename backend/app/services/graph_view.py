import json
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.constants import BEHAVIOR_LABEL, BEHAVIOR_WEIGHT
from app.graph.build import aggregate_edges, behaviors_frame, split_ranks
from app.models.tables import Behavior, Category, ModelVersion, Product, User


def graph_summary(db: Session, edge_page: int, edge_page_size: int) -> dict:
    behaviors = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "product_id": row.product_id,
            "behavior_type": row.behavior_type,
            "behavior_time": row.behavior_time,
        }
        for row in db.query(Behavior).all()
    ]
    users = {row.id: row for row in db.query(User).all()}
    products = {row.id: row for row in db.query(Product).all()}
    categories = {row.id: row for row in db.query(Category).all()}
    frame = behaviors_frame(behaviors)
    edges = aggregate_edges(frame) if not frame.empty else pd.DataFrame()
    weight_counts = {1: 0, 2: 0, 3: 0, 5: 0}
    items = []
    if not edges.empty:
        edges = edges.sort_values(["weight", "behavior_time"], ascending=[False, False])
        for weight, count in edges["weight"].value_counts().items():
            weight_counts[int(weight)] = int(count)
        start = (edge_page - 1) * edge_page_size
        for row in edges.iloc[start:start + edge_page_size].itertuples(index=False):
            user = users.get(int(row.user_id))
            product = products.get(int(row.product_id))
            category = categories.get(product.category_id) if product else None
            items.append({
                "username": user.username if user else "",
                "productName": product.name if product else "",
                "skuCode": product.sku_code if product else "",
                "categoryName": category.name if category else "",
                "behaviorType": row.behavior_type,
                "behaviorLabel": BEHAVIOR_LABEL.get(row.behavior_type, row.behavior_type),
                "weight": int(row.weight),
                "behaviorTime": pd.Timestamp(row.behavior_time).strftime("%Y-%m-%d %H:%M:%S"),
            })
    category_edges = [
        {
            "productName": product.name,
            "skuCode": product.sku_code,
            "categoryName": categories[product.category_id].name if product.category_id in categories else "",
        }
        for product in products.values()
        if product.category_id in categories
    ]
    return {
        "nodes": {
            "user": len(users),
            "product": len(products),
            "category": len(categories),
        },
        "edges": {
            "userProduct": int(len(edges)),
            "productCategory": len(category_edges),
        },
        "weightRules": [
            {"behaviorType": key, "label": BEHAVIOR_LABEL[key], "weight": BEHAVIOR_WEIGHT[key], "edgeCount": weight_counts[BEHAVIOR_WEIGHT[key]]}
            for key in ("browse", "favorite", "cart", "purchase")
        ],
        "behaviorEdges": {"total": int(len(edges)), "page": edge_page, "pageSize": edge_page_size, "items": items},
        "categoryEdges": category_edges[:20],
        "features": _feature_spec(),
        "scaler": _scaler(db),
        "split": _split(frame),
    }


def _feature_spec() -> dict:
    return {
        "user": ["性别独热", "年龄", "浏览、收藏、加购、购买次数（log1p）", "活跃天数", "距离最近行为的天数"],
        "product": ["价格（log1p）", "浏览、收藏、加购、购买次数（log1p）"],
        "category": ["类目下商品数", "类目购买次数"],
        "note": "标准化只用训练图上的均值和方差。验证集、测试集和在线预测都套用这组参数。",
    }


def _scaler(db: Session) -> dict | None:
    version = (
        db.query(ModelVersion)
        .filter(ModelVersion.algorithm == "HETERO_SAGE", ModelVersion.status == "ENABLED")
        .order_by(ModelVersion.id.desc())
        .first()
    )
    if version is None:
        version = (
            db.query(ModelVersion)
            .filter(ModelVersion.algorithm == "HETERO_SAGE")
            .order_by(ModelVersion.id.desc())
            .first()
        )
    if version is None:
        return None
    path = Path(version.artifact_path) / "norm.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "versionNo": version.version_no,
        "status": version.status,
        "ageMedian": payload.get("age_median"),
        "userMean": _round_list(payload.get("user", {}).get("mean")),
        "userStd": _round_list(payload.get("user", {}).get("std")),
        "productMean": _round_list(payload.get("product", {}).get("mean")),
        "productStd": _round_list(payload.get("product", {}).get("std")),
    }


def _split(frame: pd.DataFrame) -> dict | None:
    if frame.empty or len(frame) < 8:
        return None
    i50, i70, i85 = split_ranks(len(frame))

    def at(index: int) -> str:
        return pd.Timestamp(frame.iloc[index]["behavior_time"]).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "total": int(len(frame)),
        "historyCount": int(i50),
        "trainLabelCount": int(i70 - i50),
        "valCount": int(i85 - i70),
        "testCount": int(len(frame) - i85),
        "historyEnd": at(i50 - 1),
        "trainLabelEnd": at(i70 - 1),
        "valEnd": at(i85 - 1),
        "testStart": at(i85),
    }


def _round_list(values) -> list[float]:
    if not values:
        return []
    return [round(float(item), 4) for item in values]
