import json
import threading
from pathlib import Path

import torch
from sqlalchemy.orm import Session

from app.graph.state import graph_state
from app.models.tables import ModelVersion
from app.training.models import HeteroSAGE


class ModelRegistry:
    def __init__(self):
        self._lock = threading.RLock()
        self.model: HeteroSAGE | None = None
        self.scalers: dict | None = None
        self.meta: dict | None = None
        self.version_id: int | None = None
        self.version_no: str | None = None

    def reload(self, db: Session) -> None:
        version = (
            db.query(ModelVersion)
            .filter(ModelVersion.status == "ENABLED", ModelVersion.algorithm == "HETERO_SAGE")
            .order_by(ModelVersion.id.desc())
            .first()
        )
        with self._lock:
            if version is None:
                self.model = None
                self.scalers = None
                self.meta = None
                self.version_id = None
                self.version_no = None
                graph_state.mark_dirty()
                return
            folder = Path(version.artifact_path)
            meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
            model = HeteroSAGE(meta["user_dim"], meta["product_dim"], meta.get("category_dim", 2), meta.get("hidden", 64), meta.get("out_dim", 64))
            state = torch.load(folder / "model.pt", map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            model.eval()
            self.model = model
            self.scalers = json.loads((folder / "norm.json").read_text(encoding="utf-8"))
            self.meta = meta
            self.version_id = version.id
            self.version_no = version.version_no
            graph_state.mark_dirty()

    def snapshot(self):
        with self._lock:
            return self.model, self.scalers, self.meta, self.version_id


registry = ModelRegistry()
