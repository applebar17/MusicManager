from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

EnvironmentMode = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseModel):
    app_name: str = "Music Manager"
    environment: EnvironmentMode = "development"
    data_dir: Path = Path("local")
    temp_dir: Path = Path("local/tmp")
    database_path: Path = Path("local/music-manager.sqlite3")
    log_level: LogLevel = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)


def get_settings() -> Settings:
    return Settings()
