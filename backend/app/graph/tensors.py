"""把聚合边和特征矩阵转成模型输入。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch

from app.graph.build import aggregate_edges, involved_ids, node_features


def sample_incoming(edge_index: torch.Tensor, edge_weight: torch.Tensor, k: int, generator: torch.Generator) -> tuple[torch.Tensor, torch.Tensor]:
    if edge_index.numel() == 0 or k <= 0:
        return edge_index, edge_weight
    dest = edge_index[1].tolist()
    groups: dict[int, list[int]] = {}
    for idx, node in enumerate(dest):
        groups.setdefault(node, []).append(idx)
    keep: list[int] = []
    for indexes in groups.values():
        if len(indexes) <= k:
            keep.extend(indexes)
            continue
        perm = torch.randperm(len(indexes), generator=generator).tolist()
        keep.extend(indexes[i] for i in perm[:k])
    keep_tensor = torch.tensor(sorted(keep), dtype=torch.long)
    return edge_index[:, keep_tensor], edge_weight[keep_tensor]


def build_hetero_inputs(
    history: pd.DataFrame,
    users: pd.DataFrame,
    products: pd.DataFrame,
    categories: pd.DataFrame,
    pairs: list[tuple[int, int]],
    ref_time,
    scalers: dict | None,
    age_median: float | None,
):
    edges = aggregate_edges(history)
    user_ids, product_ids = involved_ids(edges, pairs)
    if not user_ids or not product_ids:
        raise ValueError("图中没有足够的用户或商品节点")
    product_frame = products[products["id"].isin(product_ids)] if not products.empty else products
    category_ids = sorted(int(x) for x in product_frame["category_id"].dropna().unique().tolist()) if not product_frame.empty else []
    user_x, product_x, category_x, age_median = node_features(
        history, users, products, categories, user_ids, product_ids, category_ids, ref_time, age_median
    )
    fitted = scalers is None
    if scalers is None:
        from app.graph.build import fit_scaler

        scalers = {
            "user": fit_scaler(user_x),
            "product": fit_scaler(product_x),
            "category": fit_scaler(category_x) if len(category_ids) else fit_scaler(np.zeros((1, category_x.shape[1]))),
            "age_median": age_median,
        }
    else:
        age_median = float(scalers.get("age_median", age_median or 0))
        user_x, product_x, category_x, _ = node_features(
            history, users, products, categories, user_ids, product_ids, category_ids, ref_time, age_median
        )
    from app.graph.build import apply_scaler

    user_x = apply_scaler(user_x, scalers["user"])
    product_x = apply_scaler(product_x, scalers["product"])
    if len(category_ids):
        category_x = apply_scaler(category_x, scalers["category"])
    user_index = {item_id: i for i, item_id in enumerate(user_ids)}
    product_index = {item_id: i for i, item_id in enumerate(product_ids)}
    category_index = {item_id: i for i, item_id in enumerate(category_ids)}
    device = torch.device("cpu")
    x_dict = {
        "user": torch.tensor(user_x, dtype=torch.float32, device=device),
        "product": torch.tensor(product_x, dtype=torch.float32, device=device),
        "category": torch.tensor(category_x if len(category_ids) else np.zeros((0, 2)), dtype=torch.float32, device=device),
    }
    edge_index_dict, edge_weight_dict = _relation_tensors(edges, products, user_index, product_index, category_index, device)
    return {
        "x_dict": x_dict,
        "edge_index_dict": edge_index_dict,
        "edge_weight_dict": edge_weight_dict,
        "user_index": user_index,
        "product_index": product_index,
        "category_index": category_index,
        "scalers": scalers,
        "fitted": fitted,
        "user_ids": user_ids,
        "product_ids": product_ids,
    }


def _relation_tensors(edges, products, user_index, product_index, category_index, device):
    rels = {
        ("user", "behavior", "product"): [[], []],
        ("product", "rev_behavior", "user"): [[], []],
        ("product", "belong", "category"): [[], []],
        ("category", "rev_belong", "product"): [[], []],
    }
    weights = {key: [] for key in rels}
    if not edges.empty:
        for row in edges.itertuples(index=False):
            user_id = int(row.user_id)
            product_id = int(row.product_id)
            if user_id not in user_index or product_id not in product_index:
                continue
            u = user_index[user_id]
            p = product_index[product_id]
            w = float(row.weight)
            rels[("user", "behavior", "product")][0].append(u)
            rels[("user", "behavior", "product")][1].append(p)
            weights[("user", "behavior", "product")].append(w)
            rels[("product", "rev_behavior", "user")][0].append(p)
            rels[("product", "rev_behavior", "user")][1].append(u)
            weights[("product", "rev_behavior", "user")].append(w)
    if not products.empty:
        for row in products.itertuples(index=False):
            product_id = int(row.id)
            category_id = int(row.category_id)
            if product_id not in product_index or category_id not in category_index:
                continue
            p = product_index[product_id]
            c = category_index[category_id]
            rels[("product", "belong", "category")][0].append(p)
            rels[("product", "belong", "category")][1].append(c)
            weights[("product", "belong", "category")].append(1.0)
            rels[("category", "rev_belong", "product")][0].append(c)
            rels[("category", "rev_belong", "product")][1].append(p)
            weights[("category", "rev_belong", "product")].append(1.0)
    edge_index_dict = {}
    edge_weight_dict = {}
    for key, pair in rels.items():
        if pair[0]:
            edge_index_dict[key] = torch.tensor(pair, dtype=torch.long, device=device)
            edge_weight_dict[key] = torch.tensor(weights[key], dtype=torch.float32, device=device)
        else:
            edge_index_dict[key] = torch.zeros((2, 0), dtype=torch.long, device=device)
            edge_weight_dict[key] = torch.zeros((0,), dtype=torch.float32, device=device)
    return edge_index_dict, edge_weight_dict


def stack_pairs(pairs: list[tuple[int, int, float]], user_index: dict, product_index: dict):
    users, products, labels = [], [], []
    for user_id, product_id, label in pairs:
        if user_id not in user_index or product_id not in product_index:
            continue
        users.append(user_index[user_id])
        products.append(product_index[product_id])
        labels.append(label)
    if not users:
        return None
    return (
        torch.tensor(users, dtype=torch.long),
        torch.tensor(products, dtype=torch.long),
        torch.tensor(labels, dtype=torch.float32),
    )


def homo_product_features(product_x: torch.Tensor, product_ids: list[int], products: pd.DataFrame, category_ids: list[int]) -> torch.Tensor:
    index = {cid: i for i, cid in enumerate(category_ids)}
    extra = torch.zeros((len(product_ids), len(category_ids)), dtype=torch.float32)
    product_cat = {}
    if not products.empty:
        for row in products.itertuples(index=False):
            product_cat[int(row.id)] = int(row.category_id)
    for row, product_id in enumerate(product_ids):
        cid = product_cat.get(product_id)
        if cid in index:
            extra[row, index[cid]] = 1.0
    return torch.cat([product_x, extra], dim=1)


def homo_edges(edge_index_dict, edge_weight_dict, n_users: int):
    behavior = edge_index_dict[("user", "behavior", "product")]
    weight = edge_weight_dict[("user", "behavior", "product")]
    if behavior.numel() == 0:
        empty = torch.zeros((2, 0), dtype=torch.long)
        return empty, torch.zeros((0,), dtype=torch.float32)
    src = behavior[0]
    dst = behavior[1] + n_users
    forward = torch.stack([src, dst], dim=0)
    backward = torch.stack([dst, src], dim=0)
    edge_index = torch.cat([forward, backward], dim=1)
    edge_weight = torch.cat([weight, weight], dim=0)
    return edge_index, edge_weight
