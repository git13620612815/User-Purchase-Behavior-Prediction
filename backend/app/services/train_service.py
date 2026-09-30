import pickle
import subprocess
import sys
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.constants import ALGORITHMS
from app.core.config import BACKEND_ROOT, settings
from app.core.errors import AppError
from app.core.redis import redis_client, redis_ok
from app.models.tables import Behavior, Category, Product, TrainJob, User


def fail_stale_jobs(db: Session) -> None:
    cutoff = datetime.now() - timedelta(hours=2)
    stale = db.query(TrainJob).filter(TrainJob.status == "RUNNING", TrainJob.started_at < cutoff).all()
    for job in stale:
        job.status = "FAILED"
        job.finished_at = datetime.now()
        job.log_text = ((job.log_text or "") + "\n任务超过 2 小时仍未结束，已标记失败")[-20000:]
    alive = db.query(TrainJob).filter(TrainJob.status == "RUNNING").count()
    if alive == 0:
        try:
            redis_client.delete("train:lock")
        except Exception:
            pass
    db.commit()


def start_train(db: Session, params: dict) -> TrainJob:
    _ensure_idle(db)
    algorithm = params.get("algorithm")
    if algorithm not in ALGORITHMS:
        raise AppError(40030, "算法不支持")
    _check_numbers(params)
    if db.query(Behavior).count() == 0:
        raise AppError(40023, "有效行为不足")
    return _launch(db, algorithm, {**params, "mode": "train", "seed": 42})


def start_compare(db: Session, params: dict) -> TrainJob:
    _ensure_idle(db)
    algorithms = params.get("algorithms") or list(ALGORITHMS)
    if any(item not in ALGORITHMS for item in algorithms):
        raise AppError(40030, "算法不支持")
    groups = params.get("groups")
    if not groups:
        _check_numbers(params)
        groups = [{
            "learningRate": params.get("learningRate", 0.001),
            "batchSize": params.get("batchSize", 1024),
            "epochs": params.get("epochs", 30),
        }]
    else:
        for group in groups:
            _check_numbers(group)
    if db.query(Behavior).count() == 0:
        raise AppError(40023, "有效行为不足")
    return _launch(db, "COMPARE", {
        "mode": "compare",
        "algorithms": algorithms,
        "groups": groups,
        "seed": 42,
    })


def _ensure_idle(db: Session) -> None:
    if not redis_ok():
        raise AppError(50301, "Redis 不可用", 503)
    if db.query(TrainJob).filter(TrainJob.status == "RUNNING").count():
        raise AppError(40901, "已有训练任务在执行", 409)
    if not redis_client.set("train:lock", "pending", nx=True, ex=7200):
        raise AppError(40901, "已有训练任务在执行", 409)


def _launch(db: Session, algorithm: str, params: dict) -> TrainJob:
    job = TrainJob(algorithm=algorithm, hyper_params=params, status="PENDING", log_text="", started_at=datetime.now())
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
        folder = settings.model_dir / "jobs" / str(job.id)
        folder.mkdir(parents=True, exist_ok=True)
        snapshot = folder / "snapshot.pkl"
        with snapshot.open("wb") as handle:
            pickle.dump(_snapshot(db), handle)
        params = {**params, "snapshot": str(snapshot)}
        job.hyper_params = params
        job.status = "RUNNING"
        db.commit()
        redis_client.set("train:lock", str(job.id), ex=7200)
        subprocess.Popen(
            [sys.executable, "-m", "app.training.run", "--job-id", str(job.id)],
            cwd=str(BACKEND_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return job
    except Exception:
        db.rollback()
        failed = db.get(TrainJob, job.id) if job.id else None
        if failed is not None:
            failed.status = "FAILED"
            failed.finished_at = datetime.now()
            failed.log_text = "训练进程启动失败"
            db.commit()
        redis_client.delete("train:lock")
        raise


def _snapshot(db: Session) -> dict:
    return {
        "behaviors": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "product_id": row.product_id,
                "behavior_type": row.behavior_type,
                "behavior_time": row.behavior_time,
            }
            for row in db.query(Behavior).all()
        ],
        "users": [{"id": row.id, "gender": row.gender, "age": row.age} for row in db.query(User).all()],
        "products": [
            {"id": row.id, "category_id": row.category_id, "price": float(row.price or 0)}
            for row in db.query(Product).all()
        ],
        "categories": [{"id": row.id, "name": row.name} for row in db.query(Category).all()],
    }


def _check_numbers(params: dict) -> None:
    lr = float(params.get("learningRate", 0.001))
    batch_size = int(params.get("batchSize", 1024))
    epochs = int(params.get("epochs", 30))
    if not 0 < lr < 1:
        raise AppError(40030, "学习率需大于 0 且小于 1")
    if not 1 <= batch_size <= 10000:
        raise AppError(40030, "批大小需在 1 到 10000 之间")
    if not 1 <= epochs <= 200:
        raise AppError(40030, "训练轮数需在 1 到 200 之间")
    params["learningRate"] = lr
    params["batchSize"] = batch_size
    params["epochs"] = epochs
