def ok(data=None, message: str = "ok"):
    return {"code": 0, "message": message, "data": data}


def page_args(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)
