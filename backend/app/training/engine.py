"""训练、早停和离线指标。邻居按每层 15、10 采样。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score, roc_curve

from app.graph.build import (
    history_before,
    positive_pairs,
    purchased_pairs,
    sample_negatives,
    split_ranks,
)
from app.graph.tensors import (
    build_hetero_inputs,
    homo_edges,
    homo_product_features,
    sample_incoming,
    stack_pairs,
)
from app.training.models import HeteroSAGE, HomoEncoder


def train_algorithm(
    df: pd.DataFrame,
    users: pd.DataFrame,
    products: pd.DataFrame,
    categories: pd.DataFrame,
    algorithm: str,
    learning_rate: float,
    batch_size: int,
    epochs: int,
    seed: int,
    artifact_dir: Path,
    curve_dir: Path,
    log,
) -> dict:
    i50, i70, i85 = split_ranks(len(df))
    product_ids = [int(x) for x in products["id"].tolist()]
    train_pos = positive_pairs(df, i50, i70)
    val_pos = positive_pairs(df, i70, i85)
    test_pos = positive_pairs(df, i85, None)
    if len(train_pos) < 1:
        raise ValueError("有效购买样本不足，无法按时间切分")
    train_pairs = sample_negatives(train_pos, _banned(df, i70), product_ids, seed)
    val_pairs = sample_negatives(val_pos, _banned(df, i85), product_ids, seed + 1) if val_pos else []
    test_pairs = sample_negatives(test_pos, _banned(df, len(df) + 1), product_ids, seed + 2) if test_pos else []
    train_hist = history_before(df, i50)
    ref_time = train_hist["behavior_time"].max().to_pydatetime()
    train_pack = build_hetero_inputs(
        train_hist, users, products, categories, [(u, p) for u, p, _ in train_pairs], ref_time, None, None
    )
    scalers = train_pack["scalers"]
    val_pack = _pack_or_none(df, users, products, categories, val_pairs, i70, scalers)
    test_pack = _pack_or_none(df, users, products, categories, test_pairs, i85, scalers)
    category_ids = sorted(int(x) for x in categories["id"].tolist()) if not categories.empty else []
    model = _make_model(algorithm, train_pack, products, category_ids)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    generator = torch.Generator().manual_seed(seed)
    best_state = None
    best_auc = -1.0
    wait = 0
    history = []
    for epoch in range(1, epochs + 1):
        loss = _epoch(model, algorithm, train_pack, train_pairs, batch_size, optimizer, generator, products, category_ids)
        val_auc = _auc(model, algorithm, val_pack, val_pairs, products, category_ids) if val_pack and val_pairs else None
        history.append({"epoch": epoch, "trainLoss": round(loss, 6), "valAuc": None if val_auc is None else round(float(val_auc), 6)})
        log(f"epoch {epoch} loss={loss:.4f} val_auc={val_auc}")
        if val_auc is None or float(val_auc) > best_auc + 1e-4:
            best_auc = -1.0 if val_auc is None else float(val_auc)
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
        if val_auc is not None and wait >= 5:
            log("验证集 AUC 连续 5 轮未提升，提前停止")
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    metrics = _ranking_metrics(model, algorithm, test_pack, test_pairs, test_pos, df, i85, products, categories, category_ids)
    roc = _roc_points(model, algorithm, test_pack, test_pairs, products, category_ids)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    curve_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), artifact_dir / "model.pt")
    (artifact_dir / "norm.json").write_text(json.dumps(scalers, ensure_ascii=False), encoding="utf-8")
    meta = {
        "algorithm": algorithm,
        "user_dim": int(train_pack["x_dict"]["user"].size(1)),
        "product_dim": int(train_pack["x_dict"]["product"].size(1)),
        "category_dim": 2,
        "hidden": 64,
        "out_dim": 64,
        "category_ids": category_ids,
        "neighbors": [15, 10],
    }
    if algorithm != "HETERO_SAGE":
        meta["homo_product_dim"] = int(train_pack["x_dict"]["product"].size(1) + len(category_ids))
    (artifact_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (curve_dir / "loss.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
    (curve_dir / "roc.json").write_text(json.dumps(roc, ensure_ascii=False), encoding="utf-8")
    metrics["bestValAuc"] = None if best_auc < 0 else round(best_auc, 6)
    return metrics


def _banned(df: pd.DataFrame, rank_end: int) -> dict[int, set[int]]:
    pairs = purchased_pairs(df, rank_end)
    banned: dict[int, set[int]] = {}
    for user_id, product_id in pairs:
        banned.setdefault(user_id, set()).add(product_id)
    return banned


def _pack_or_none(df, users, products, categories, pairs, cutoff, scalers):
    if not pairs:
        return None
    history = history_before(df, cutoff)
    ref_time = history["behavior_time"].max().to_pydatetime() if not history.empty else df["behavior_time"].min().to_pydatetime()
    return build_hetero_inputs(
        history,
        users,
        products,
        categories,
        [(u, p) for u, p, _ in pairs],
        ref_time,
        scalers,
        scalers.get("age_median"),
    )


def _make_model(algorithm, pack, products, category_ids):
    user_dim = pack["x_dict"]["user"].size(1)
    product_dim = pack["x_dict"]["product"].size(1)
    if algorithm == "HETERO_SAGE":
        return HeteroSAGE(user_dim, product_dim, 2)
    homo_dim = product_dim + len(category_ids)
    return HomoEncoder(user_dim, homo_dim, kind="GCN" if algorithm == "GCN" else "GAT")


def _sampled_edges(pack, generator):
    first_index, first_weight, second_index, second_weight = {}, {}, {}, {}
    for key, edge_index in pack["edge_index_dict"].items():
        weight = pack["edge_weight_dict"][key]
        e15, w15 = sample_incoming(edge_index, weight, 15, generator)
        e10, w10 = sample_incoming(e15, w15, 10, generator)
        first_index[key], first_weight[key] = e15, w15
        second_index[key], second_weight[key] = e10, w10
    return first_index, first_weight, second_index, second_weight


def _forward(model, algorithm, pack, products, category_ids, generator):
    if algorithm == "HETERO_SAGE":
        e1, w1, e2, w2 = _sampled_edges(pack, generator)
        out = model(pack["x_dict"], e1, w1, e2, w2)
        return out["user"], out["product"]
    product_x = homo_product_features(pack["x_dict"]["product"], pack["product_ids"], products, category_ids)
    edge_index, edge_weight = homo_edges(pack["edge_index_dict"], pack["edge_weight_dict"], pack["x_dict"]["user"].size(0))
    e15, w15 = sample_incoming(edge_index, edge_weight, 15, generator)
    return model(pack["x_dict"]["user"], product_x, e15, w15)


def _epoch(model, algorithm, pack, pairs, batch_size, optimizer, generator, products, category_ids) -> float:
    stacked = stack_pairs(pairs, pack["user_index"], pack["product_index"])
    if stacked is None:
        return 0.0
    users, products_idx, labels = stacked
    order = torch.randperm(users.size(0), generator=generator)
    model.train()
    total = 0.0
    seen = 0
    batch_size = max(1, batch_size)
    for start in range(0, users.size(0), batch_size):
        choose = order[start:start + batch_size]
        optimizer.zero_grad()
        user_emb, product_emb = _forward(model, algorithm, pack, products, category_ids, generator)
        logits = (user_emb[users[choose]] * product_emb[products_idx[choose]]).sum(dim=-1)
        loss = F.binary_cross_entropy_with_logits(logits, labels[choose])
        loss.backward()
        optimizer.step()
        total += float(loss.detach()) * choose.numel()
        seen += choose.numel()
    return total / max(seen, 1)


@torch.no_grad()
def _scores(model, algorithm, pack, pairs, products, category_ids):
    stacked = stack_pairs(pairs, pack["user_index"], pack["product_index"])
    if stacked is None:
        return None, None
    model.eval()
    generator = torch.Generator().manual_seed(0)
    user_emb, product_emb = _forward(model, algorithm, pack, products, category_ids, generator)
    users, products_idx, labels = stacked
    logits = (user_emb[users] * product_emb[products_idx]).sum(dim=-1)
    return torch.sigmoid(logits).cpu().numpy(), labels.cpu().numpy()


def _auc(model, algorithm, pack, pairs, products, category_ids):
    if pack is None or not pairs:
        return None
    probs, labels = _scores(model, algorithm, pack, pairs, products, category_ids)
    if probs is None or len(set(labels.tolist())) < 2:
        return None
    return float(roc_auc_score(labels, probs))


def _roc_points(model, algorithm, pack, pairs, products, category_ids):
    if pack is None or not pairs:
        return []
    probs, labels = _scores(model, algorithm, pack, pairs, products, category_ids)
    if probs is None or len(set(labels.tolist())) < 2:
        return []
    fpr, tpr, _ = roc_curve(labels, probs)
    if len(fpr) > 100:
        idx = np.linspace(0, len(fpr) - 1, 100).astype(int)
        fpr, tpr = fpr[idx], tpr[idx]
    return [{"fpr": round(float(a), 6), "tpr": round(float(b), 6)} for a, b in zip(fpr, tpr)]


def _ranking_metrics(model, algorithm, pack, pairs, positives, df, cutoff, products, categories, category_ids):
    auc = _auc(model, algorithm, pack, pairs, products, category_ids)
    precision_sum = 0.0
    recall_sum = 0.0
    users = 0
    if pack is not None and positives:
        model.eval()
        generator = torch.Generator().manual_seed(0)
        user_emb, product_emb = _forward(model, algorithm, pack, products, category_ids, generator)
        history = history_before(df, cutoff)
        purchased_by_user: dict[int, set[int]] = {}
        for bought_user, bought_product in purchased_pairs(df, cutoff):
            purchased_by_user.setdefault(bought_user, set()).add(bought_product)
        by_user: dict[int, set[int]] = {}
        for user_id, product_id in positives:
            by_user.setdefault(user_id, set()).add(product_id)
        cat_of = {}
        if not products.empty:
            for row in products.itertuples(index=False):
                cat_of[int(row.id)] = int(row.category_id)
        hot = _hot_products(history)
        for user_id, truth in by_user.items():
            if user_id not in pack["user_index"]:
                continue
            candidates = _candidates(history, user_id, purchased_by_user.get(user_id, set()), cat_of, hot, pack["product_index"])
            if not candidates:
                continue
            uvec = user_emb[pack["user_index"][user_id]]
            ranked = []
            for product_id in candidates:
                ivec = product_emb[pack["product_index"][product_id]]
                score = float(torch.dot(uvec, ivec))
                ranked.append((score, product_id))
            ranked.sort(reverse=True)
            top = {product_id for _, product_id in ranked[:10]}
            hits = len(top & truth)
            precision_sum += hits / min(10, len(ranked))
            recall_sum += hits / max(len(truth), 1)
            users += 1
    precision = precision_sum / users if users else 0.0
    recall = recall_sum / users if users else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {
        "auc": None if auc is None else round(float(auc), 6),
        "precisionAt10": round(precision, 6),
        "recallAt10": round(recall, 6),
        "f1": round(f1, 6),
    }


def _hot_products(history: pd.DataFrame) -> list[int]:
    if history.empty:
        return []
    bought = history[history["behavior_type"] == "purchase"]
    if bought.empty:
        return []
    return [int(x) for x in bought.groupby("product_id").size().sort_values(ascending=False).index.tolist()]


def _candidates(history, user_id, purchased, cat_of, hot, product_index) -> list[int]:
    own = history[history["user_id"] == user_id] if not history.empty else history
    categories = set()
    interacted = []
    if not own.empty:
        for product_id in own["product_id"].tolist():
            product_id = int(product_id)
            if product_id in purchased or product_id not in product_index:
                continue
            interacted.append(product_id)
            if product_id in cat_of:
                categories.add(cat_of[product_id])
    in_cat = [pid for pid, cid in cat_of.items() if cid in categories and pid not in purchased and pid in product_index]
    hot_cat = [pid for pid in hot if pid in in_cat]
    ordered = []
    for pid in interacted + hot_cat + in_cat + hot:
        if pid in purchased or pid not in product_index or pid in ordered:
            continue
        ordered.append(pid)
        if len(ordered) >= 100:
            break
    return ordered
