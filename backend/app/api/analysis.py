from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.common import ok
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.tables import User
from app.services.stats_service import user_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/me")
def my_analysis(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ok(user_analysis(db, user.id))
