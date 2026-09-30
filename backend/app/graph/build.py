"""构图、时间切分和特征。训练图只使用切分点之前的行为。"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from app.constants import BEHAVIOR_WEIGHT, GENDER_ORDER

USER_DIM = 10
PRODUCT_DIM = 5
CATEGORY_DIM = 2


def behaviors_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["behavior_time"] = pd.to_datetime(df["behavior_time"])
    df = df.sort_values(["behavior_time", "id"]).reset_index(drop=True)
    df["rank"] = np.arange(len(df))
    return df


def split_ranks(n: int) -> tuple[int, int, int]:
    """前 50% 作为训练图历史，50%–70% 为训练标签，70%–85% 验证，最后 15% 测试。

    最早的 70% 时间窗内部再留出历史，否则训练图为空，无法学习。
    """
    if n < 8:
        raise ValueError("有效行为不足，无法按时间切分")
    i50 = max(1, int(n * 0.50))
    i70 = max(i50 + 1, int(n * 0.70))
    i85 = max(i70 + 1, int(n * 0.85))
    i85 = min(i85, n - 1)
    if not (0 < i50 < i70 < i85 < n):
        raise ValueError("有效行为不足，无法按时间切分")
    return i50, i70, i85


def _gender_one_hot(value: str | None) -> list[float]:
    text = value if value in GENDER_ORDER else "未知"
    return [1.0 if text == name else 0.0 for name in GENDER_ORDER]


def aggregate_edges(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["user_id", "product_id", "weight", "behavior_type", "behavior_time"])
    work = df.copy()
    work["weight"] = work["behavior_type"].map(BEHAVIOR_WEIGHT).astype(int)
    work = work.sort_values(["weight", "behavior_time"])
    # 同一用户-商品只保留最强行为；权重相同则保留最近时间
    kept = work.groupby(["user_id", "product_id"], as_index=False).tail(1)
    return kept[["user_id", "product_id", "weight", "behavior_type", "behavior_time"]]


def purchased_pairs(df: pd.DataFrame, rank_end: int) -> set[tuple[int, int]]:
    sub = df[(df["rank"] < rank_end) & (df["behavior_type"] == "purchase")]
    return set(zip(sub["user_id"].tolist(), sub["product_id"].tolist()))


def positive_pairs(df: pd.DataFrame, rank_start: int, rank_end: int | None) -> list[tuple[int, int]]:
    sub = df[df["rank"] >= rank_start]
    if rank_end is not None:
        sub = sub[sub["rank"] < rank_end]
    sub = sub[sub["behavior_type"] == "purchase"]
    before = purchased_pairs(df, rank_start)
    pairs = []
    seen = set()
    for user_id, product_id in zip(sub["user_id"].tolist(), sub["product_id"].tolist()):
        key = (int(user_id), int(product_id))
        if key in before or key in seen:
            continue
        seen.add(key)
        pairs.append(key)
    return pairs


def sample_negatives(
    positives: list[tuple[int, int]],
    banned: dict[int, set[int]],
    product_ids: list[int],
    seed: int,
    ratio: int = 4,
) -> list[tuple[int, int, float]]:
    rng = np.random.default_rng(seed)
    samples: list[tuple[int, int, float]] = [(u, p, 1.0) for u, p in positives]
    catalog = np.array(product_ids, dtype=np.int64)
    for user_id, _product_id in positives:
        block = banned.get(user_id, set())
        pool = catalog[~np.isin(catalog, list(block) or [-1])]
        if pool.size == 0:
            continue
        take = min(ratio, int(pool.size))
        picked = rng.choice(pool, size=take, replace=False)
        for product_id in np.atleast_1d(picked):
            samples.append((user_id, int(product_id), 0.0))
    return samples


def _count_matrix(df: pd.DataFrame, ids: list[int], id_col: str) -> np.ndarray:
    types = ["browse", "favorite", "cart", "purchase"]
    matrix = np.zeros((len(ids), 4), dtype=np.float64)
    if df.empty or not ids:
        return matrix
    index = {item_id: i for i, item_id in enumerate(ids)}
    grouped = df.groupby([id_col, "behavior_type"]).size()
    for (item_id, behavior_type), count in grouped.items():
        row = index.get(int(item_id))
        if row is None or behavior_type not in types:
            continue
        matrix[row, types.index(behavior_type)] = float(count)
    return matrix


def node_features(
    history: pd.DataFrame,
    users: pd.DataFrame,
    products: pd.DataFrame,
    categories: pd.DataFrame,
    user_ids: list[int],
    product_ids: list[int],
    category_ids: list[int],
    ref_time: datetime,
    age_median: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    user_index = users.set_index("id") if not users.empty else None
    ages = []
    if user_index is not None and "age" in users.columns:
        ages = [float(a) for a in users["age"].dropna().tolist()]
    if age_median is None:
        age_median = float(np.median(ages)) if ages else 0.0

    user_counts = _count_matrix(history, user_ids, "user_id")
    product_counts = _count_matrix(history, product_ids, "product_id")
    user_x = np.zeros((len(user_ids), USER_DIM), dtype=np.float64)
    last_time = {}
    active_days = {}
    if not history.empty:
        for user_id, grp in history.groupby("user_id"):
            last_time[int(user_id)] = grp["behavior_time"].max().to_pydatetime()
            active_days[int(user_id)] = grp["behavior_time"].dt.date.nunique()
    for row, user_id in enumerate(user_ids):
        gender = None
        age = None
        if user_index is not None and user_id in user_index.index:
            record = user_index.loc[user_id]
            gender = None if pd.isna(record.get("gender")) else record.get("gender")
            raw_age = record.get("age")
            age = None if pd.isna(raw_age) else float(raw_age)
        user_x[row, 0:3] = _gender_one_hot(gender)
        user_x[row, 3] = age_median if age is None else age
        user_x[row, 4:8] = np.log1p(user_counts[row])
        user_x[row, 8] = float(active_days.get(user_id, 0))
        latest = last_time.get(user_id)
        user_x[row, 9] = 0.0 if latest is None else max((ref_time - latest).total_seconds() / 86400.0, 0.0)

    product_index = products.set_index("id") if not products.empty else None
    product_x = np.zeros((len(product_ids), PRODUCT_DIM), dtype=np.float64)
    for row, product_id in enumerate(product_ids):
        price = 0.0
        if product_index is not None and product_id in product_index.index:
            price = float(product_index.loc[product_id]["price"] or 0)
        product_x[row, 0] = np.log1p(max(price, 0.0))
        product_x[row, 1:5] = np.log1p(product_counts[row])

    purchase_by_cat = {}
    if not history.empty and not products.empty:
        merged = history.merge(products[["id", "category_id"]], left_on="product_id", right_on="id", how="left")
        bought = merged[merged["behavior_type"] == "purchase"]
        purchase_by_cat = bought.groupby("category_id").size().to_dict()
    cat_product_count = products.groupby("category_id").size().to_dict() if not products.empty else {}
    category_x = np.zeros((len(category_ids), CATEGORY_DIM), dtype=np.float64)
    for row, category_id in enumerate(category_ids):
        category_x[row, 0] = float(cat_product_count.get(category_id, 0))
        category_x[row, 1] = float(purchase_by_cat.get(category_id, 0))
    return user_x, product_x, category_x, float(age_median)


def fit_scaler(matrix: np.ndarray) -> dict:
    if matrix.size == 0:
        dim = matrix.shape[1] if matrix.ndim == 2 else 1
        mean = np.zeros(dim)
        std = np.ones(dim)
    else:
        mean = matrix.mean(axis=0)
        std = matrix.std(axis=0)
        std = np.where(std < 1e-6, 1.0, std)
    return {"mean": mean.tolist(), "std": std.tolist()}


def apply_scaler(matrix: np.ndarray, scaler: dict) -> np.ndarray:
    mean = np.array(scaler["mean"], dtype=np.float64)
    std = np.array(scaler["std"], dtype=np.float64)
    std = np.where(std < 1e-6, 1.0, std)
    return (matrix - mean) / std


def history_before(df: pd.DataFrame, rank_end: int) -> pd.DataFrame:
    return df[df["rank"] < rank_end].copy()


def involved_ids(edges: pd.DataFrame, pairs: list[tuple[int, int]]) -> tuple[list[int], list[int]]:
    users = set(int(x) for x in edges["user_id"].tolist()) if not edges.empty else set()
    products = set(int(x) for x in edges["product_id"].tolist()) if not edges.empty else set()
    for user_id, product_id in pairs:
        users.add(int(user_id))
        products.add(int(product_id))
    return sorted(users), sorted(products)
