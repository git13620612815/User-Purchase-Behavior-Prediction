"""在线推理：用已启用的 HeteroSAGE 对候选商品打分。"""

from __future__ import annotations

import threading

import pandas as pd
import torch
from sqlalchemy.orm import Session

from app.constants import BEHAVIOR_WEIGHT
from app.graph.build import behaviors_frame
from app.graph.registry import registry
from app.graph.state import graph_state
from app.graph.tensors import build_hetero_inputs, sample_incoming
from app.models.tables import Behavior, Category, Product, User

_cache_lock = threading.Lock()
_cache: dict = {"generation": -1, "version_id": None, "pack": None, "user_emb": None, "product_emb": None}


def score_user(db: Session, user_id: int, focus_product_id: int | None = None) -> tuple[list[dict], float | None]:
    pack, user_emb, product_emb = _embeddings(db)
    if pack is None or user_id not in pack["user_index"]:
        return [], None
    history = pack["history"]
    purchased = set(
        int(pid)
        for pid in history[(history["user_id"] == user_id) & (history["behavior_type"] == "purchase")]["product_id"].tolist()
    ) if not history.empty else set()
    cat_of = pack["cat_of"]
    hot = pack["hot"]
    uvec = user_emb[pack["user_index"][user_id]]
    focus_probability = _probability(uvec, product_emb, pack["product_index"], focus_product_id, purchased)
    candidates = _candidates(history, user_id, purchased, cat_of, hot, pack["product_index"])
    scored = []
    for product_id in candidates:
        prob = _probability(uvec, product_emb, pack["product_index"], product_id, purchased)
        if prob is None:
            continue
        scored.append((prob, product_id))
    scored.sort(reverse=True)
    items = [{"productId": product_id, "probability": probability} for probability, product_id in scored[:10]]
    return items, focus_probability


def _probability(user_vec, product_emb, product_index, product_id: int | None, purchased: set[int]) -> float | None:
    if product_id is None or product_id in purchased or product_id not in product_index:
        return None
    logit = float(torch.dot(user_vec, product_emb[product_index[product_id]]))
    probability = float(torch.sigmoid(torch.tensor(logit)).item())
    return round(max(0.0, min(1.0, probability)), 4)


def _embeddings(db: Session):
    model, scalers, _meta, version_id = registry.snapshot()
    if model is None or scalers is None or version_id is None:
        return None, None, None
    generation = graph_state.generation
    with _cache_lock:
        if _cache["generation"] == generation and _cache["version_id"] == version_id and _cache["user_emb"] is not None:
            return _cache["pack"], _cache["user_emb"], _cache["product_emb"]
        pack = _load_pack(db, scalers)
        model.eval()
        generator = torch.Generator().manual_seed(0)
        first_index, first_weight, second_index, second_weight = {}, {}, {}, {}
        for key, edge_index in pack["edge_index_dict"].items():
            weight = pack["edge_weight_dict"][key]
            e15, w15 = sample_incoming(edge_index, weight, 15, generator)
            e10, w10 = sample_incoming(e15, w15, 10, generator)
            first_index[key], first_weight[key] = e15, w15
            second_index[key], second_weight[key] = e10, w10
        with torch.no_grad():
            out = model(pack["x_dict"], first_index, first_weight, second_index, second_weight)
        user_emb = out["user"].detach()
        product_emb = out["product"].detach()
        _cache.update({"generation": generation, "version_id": version_id, "pack": pack, "user_emb": user_emb, "product_emb": product_emb})
        return pack, user_emb, product_emb


def _load_pack(db: Session, scalers: dict):
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
    df = behaviors_frame(behaviors)
    users = pd.DataFrame([{"id": row.id, "gender": row.gender, "age": row.age} for row in db.query(User).all()])
    products = pd.DataFrame([
        {"id": row.id, "category_id": row.category_id, "price": float(row.price or 0), "name": row.name}
        for row in db.query(Product).all()
    ])
    categories = pd.DataFrame([{"id": row.id, "name": row.name} for row in db.query(Category).all()])
    ref_time = df["behavior_time"].max().to_pydatetime() if not df.empty else __import__("datetime").datetime.now()
    pack = build_hetero_inputs(df, users, products, categories, [], ref_time, scalers, scalers.get("age_median"))
    pack["history"] = df
    pack["cat_of"] = {int(row.id): int(row.category_id) for row in products.itertuples(index=False)} if not products.empty else {}
    pack["hot"] = _hot(df)
    return pack


def _hot(df: pd.DataFrame) -> list[int]:
    if df.empty:
        return []
    bought = df[df["behavior_type"] == "purchase"]
    if bought.empty:
        return []
    return [int(x) for x in bought.groupby("product_id").size().sort_values(ascending=False).index.tolist()]


def _candidates(history, user_id, purchased, cat_of, hot, product_index) -> list[int]:
    own = history[history["user_id"] == user_id] if not history.empty else history
    categories = set()
    interacted = []
    weights = {}
    if not own.empty:
        for row in own.itertuples(index=False):
            product_id = int(row.product_id)
            weight = BEHAVIOR_WEIGHT.get(row.behavior_type, 0)
            weights[product_id] = max(weights.get(product_id, 0), weight)
            if product_id in cat_of:
                categories.add(cat_of[product_id])
    interacted = sorted((pid for pid in weights if pid not in purchased and pid in product_index), key=lambda pid: weights[pid], reverse=True)
    in_cat = [pid for pid, cid in cat_of.items() if cid in categories and pid not in purchased and pid in product_index]
    hot_rank = {pid: i for i, pid in enumerate(hot)}
    in_cat.sort(key=lambda pid: hot_rank.get(pid, 10**9))
    hot_cat = [pid for pid in hot if pid in set(in_cat)]
    ordered = []
    seen = set()
    for pid in interacted + hot_cat + in_cat + hot:
        if pid in purchased or pid not in product_index or pid in seen:
            continue
        seen.add(pid)
        ordered.append(pid)
        if len(ordered) >= 100:
            break
    return ordered
