from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.common import ok
from app.core.database import get_db
from app.core.deps import bearer, get_current_user
from app.core.errors import AppError
from app.core.security import USERNAME_RE, PASSWORD_RE, blacklist_token, create_token, decode_token, hash_password, verify_password
from app.models.tables import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str
    password: str
    nickname: str | None = None


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    _check_account(body.username, body.password)
    if db.query(User).filter(User.username == body.username).first():
        raise AppError(40001, "用户名已存在")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname or body.username,
        gender="未知",
        role="USER",
        status="ENABLED",
    )
    db.add(user)
    db.commit()
    return ok({"id": user.id, "username": user.username})


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(40101, "用户名或密码错误", 401)
    if user.status != "ENABLED":
        raise AppError(40301, "账号已停用", 403)
    token = create_token(user.id, user.role)
    return ok({"accessToken": token, "role": user.role, "username": user.username, "userId": user.id})


@router.post("/logout")
def logout(credentials=Depends(bearer), user: User = Depends(get_current_user)):
    if credentials is not None:
        try:
            blacklist_token(decode_token(credentials.credentials))
        except Exception:
            pass
    return ok({"username": user.username})


def _check_account(username: str, password: str) -> None:
    if not USERNAME_RE.match(username or ""):
        raise AppError(40001, "用户名需为 4 到 32 位字母或数字")
    if not PASSWORD_RE.match(password or ""):
        raise AppError(40001, "密码至少 8 位，且同时包含字母和数字")
