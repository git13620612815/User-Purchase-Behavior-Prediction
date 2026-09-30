"""训练子进程入口：python -m app.training.run --job-id 1"""

from __future__ import annotations

import argparse
import pickle
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis import redis_client
from app.graph.build import behaviors_frame
from app.models.tables import ModelVersion, TrainJob
from app.training.engine import train_algorithm

PREFIX = {"HETERO_SAGE": "sage", "GCN": "gcn", "GAT": "gat"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", type=int, required=True)
    args = parser.parse_args()
    db = SessionLocal()
    job = db.get(TrainJob, args.job_id)
    if job is None:
        return
    try:
        params = job.hyper_params or {}
        snapshot_path = Path(params["snapshot"])
        with snapshot_path.open("rb") as handle:
            snapshot = pickle.load(handle)
        df = behaviors_frame(snapshot["behaviors"])
        users = pd.DataFrame(snapshot["users"])
        products = pd.DataFrame(snapshot["products"])
        categories = pd.DataFrame(snapshot["categories"])
        if products.empty or df.empty:
            raise ValueError("有效行为不足")
        mode = params.get("mode", "train")
        if mode == "compare":
            algorithms = params.get("algorithms") or ["HETERO_SAGE", "GCN", "GAT"]
            groups = params.get("groups") or [{
                "learningRate": params.get("learningRate", 0.001),
                "batchSize": params.get("batchSize", 1024),
                "epochs": params.get("epochs", 30),
            }]
            tasks = [(alg, group) for group in groups for alg in algorithms]
        else:
            tasks = [(job.algorithm, params)]
        for index, (algorithm, group) in enumerate(tasks, start=1):
            _append(db, job, f"开始 {algorithm} 学习率={group.get('learningRate')} 批大小={group.get('batchSize')} 轮数={group.get('epochs')}")
            version_no = f"{PREFIX.get(algorithm, algorithm.lower())}-{datetime.now():%Y%m%d-%H%M%S}-{index}"
            artifact = settings.model_dir / version_no
            curve = settings.curve_dir / version_no
            metrics = train_algorithm(
                df,
                users,
                products,
                categories,
                algorithm,
                float(group.get("learningRate", 0.001)),
                int(group.get("batchSize", 1024)),
                int(group.get("epochs", 30)),
                int(params.get("seed", 42)),
                artifact,
                curve,
                lambda message: _append(db, job, message),
            )
            version = ModelVersion(
                algorithm=algorithm,
                version_no=version_no,
                hyper_params={
                    "learningRate": float(group.get("learningRate", 0.001)),
                    "batchSize": int(group.get("batchSize", 1024)),
                    "epochs": int(group.get("epochs", 30)),
                    "seed": int(params.get("seed", 42)),
                    "neighbors": [15, 10],
                },
                metrics=metrics,
                artifact_path=str(artifact),
                status="TRAINED",
                is_online_allowed=1 if algorithm == "HETERO_SAGE" else 0,
            )
            db.add(version)
            db.commit()
            _append(db, job, f"完成 {version_no} 指标={metrics}")
        job.status = "SUCCESS"
        job.finished_at = datetime.now()
        db.commit()
    except Exception:
        db.rollback()
        job = db.get(TrainJob, args.job_id)
        if job is not None:
            job.status = "FAILED"
            job.finished_at = datetime.now()
            job.log_text = ((job.log_text or "") + "\n" + traceback.format_exc())[-20000:]
            db.commit()
    finally:
        try:
            redis_client.delete("train:lock")
        except Exception:
            pass
        db.close()


def _append(db, job: TrainJob, message: str) -> None:
    job.log_text = ((job.log_text or "") + "\n" + message)[-20000:]
    db.commit()


if __name__ == "__main__":
    main()
