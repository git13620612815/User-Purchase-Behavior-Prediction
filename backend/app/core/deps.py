import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_token, is_blacklisted
from app.models.tables import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AppError(40100, "请先登录", 401)
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise AppError(40100, "登录已失效", 401)
    if is_blacklisted(payload.get("jti")):
        raise AppError(40100, "登录已失效", 401)
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise AppError(40100, "登录已失效", 401)
    if user.status != "ENABLED":
        raise AppError(40301, "账号已停用", 403)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise AppError(40300, "需要管理员权限", 403)
    return user
