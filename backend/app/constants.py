BEHAVIOR_WEIGHT = {
    "browse": 1,
    "favorite": 2,
    "cart": 3,
    "purchase": 5,
}

BEHAVIOR_LABEL = {
    "browse": "浏览",
    "favorite": "收藏",
    "cart": "加购",
    "purchase": "购买",
}

SOURCE_LABEL = {
    "GNN": "图神经网络",
    "POPULAR": "热门商品",
}

ALGORITHMS = ("HETERO_SAGE", "GCN", "GAT")
ONLINE_ALGORITHM = "HETERO_SAGE"
GENDER_ORDER = ("男", "女", "未知")
HEADER_MAP = {
    "user": ["username", "nickname", "gender", "age", "phone", "email", "register_time"],
    "product": ["sku_code", "name", "category_name", "price"],
    "behavior": ["username", "sku_code", "behavior_type", "behavior_time"],
}
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MIN_TIME = __import__("datetime").datetime(2000, 1, 1)
