from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.common import ok
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.security import PASSWORD_RE, hash_password, verify_password
from app.models.tables import User

router = APIRouter(prefix="/users", tags=["users"])


class ProfileBody(BaseModel):
    nickname: str | None = None
    gender: str | None = None
    age: int | None = None
    phone: str | None = None
    email: str | None = None


class PasswordBody(BaseModel):
    oldPassword: str
    newPassword: str


def user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "phone": user.phone,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "createdAt": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok(user_dict(user))


@router.put("/me")
def update_me(body: ProfileBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.gender is not None and body.gender not in ("男", "女", "未知"):
        raise AppError(40002, "性别不合法")
    if body.age is not None and not 0 <= body.age <= 120:
        raise AppError(40002, "年龄不合法")
    for field in ("nickname", "gender", "age", "phone", "email"):
        value = getattr(body, field)
        if value is not None:
            setattr(user, field, value)
    db.commit()
    return ok(user_dict(user))


@router.put("/me/password")
def update_password(body: PasswordBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(body.oldPassword, user.password_hash):
        raise AppError(40002, "原密码不正确")
    if not PASSWORD_RE.match(body.newPassword or ""):
        raise AppError(40002, "密码至少 8 位，且同时包含字母和数字")
    user.password_hash = hash_password(body.newPassword)
    db.commit()
    return ok()
