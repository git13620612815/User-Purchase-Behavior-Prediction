from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin import router as admin_router
from app.api.analysis import router as analysis_router
from app.api.auth import router as auth_router
from app.api.behaviors import router as behavior_router
from app.api.catalog import router as catalog_router
from app.api.predictions import router as prediction_router
from app.api.users import router as user_router
from app.core.database import Base, SessionLocal, engine
from app.core.errors import AppError
from app.core.security import hash_password
from app.graph.registry import registry
from app.models.tables import User
from app.services.train_service import fail_stale_jobs


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == "admin").first() is None:
            db.add(User(
                username="admin",
                password_hash=hash_password("Admin12345"),
                nickname="管理员",
                gender="未知",
                role="ADMIN",
                status="ENABLED",
            ))
            db.commit()
        fail_stale_jobs(db)
        registry.reload(db)
    finally:
        db.close()
    yield


app = FastAPI(title="用户购买行为预测", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for item in (auth_router, user_router, catalog_router, behavior_router, prediction_router, analysis_router, admin_router):
    app.include_router(item, prefix="/api")


@app.exception_handler(AppError)
def handle_app_error(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message, "data": None})


@app.exception_handler(RequestValidationError)
def handle_validation(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": 42200, "message": "参数不正确", "data": exc.errors()})


@app.get("/api/health")
def health():
    return {"code": 0, "message": "ok", "data": {"status": "up"}}
