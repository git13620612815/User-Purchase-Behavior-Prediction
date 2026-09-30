from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "mysql+pymysql://root:888888@127.0.0.1:3306/purchase_predict?charset=utf8mb4"
    redis_url: str = "redis://127.0.0.1:6379/0"
    jwt_secret: str = "purchase-predict-dev-secret"
    jwt_expire_minutes: int = 120
    data_dir: str = str(PROJECT_ROOT / "data")

    @property
    def import_dir(self) -> Path:
        return Path(self.data_dir) / "import"

    @property
    def model_dir(self) -> Path:
        return Path(self.data_dir) / "models"

    @property
    def curve_dir(self) -> Path:
        return Path(self.data_dir) / "curves"


settings = Settings()
for _path in (settings.import_dir, settings.model_dir, settings.curve_dir):
    _path.mkdir(parents=True, exist_ok=True)
