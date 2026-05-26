import os
from pathlib import Path
from typing import Literal, cast

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
    log_console_level: LogLevel = "WARNING"
    log_file_level: LogLevel = "DEBUG"
    log_file_path: Path = Path("local/logs/backend.log")
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)


def get_settings() -> Settings:
    return Settings(
        environment=cast(EnvironmentMode, os.getenv("MUSIC_MANAGER_ENVIRONMENT", "development")),
        data_dir=Path(os.getenv("MUSIC_MANAGER_DATA_DIR", "local")),
        temp_dir=Path(os.getenv("MUSIC_MANAGER_TEMP_DIR", "local/tmp")),
        database_path=Path(os.getenv("MUSIC_MANAGER_DATABASE_PATH", "local/music-manager.sqlite3")),
        log_level=cast(LogLevel, os.getenv("MUSIC_MANAGER_LOG_LEVEL", "INFO")),
        log_console_level=cast(
            LogLevel,
            os.getenv("MUSIC_MANAGER_LOG_CONSOLE_LEVEL", "WARNING"),
        ),
        log_file_level=cast(LogLevel, os.getenv("MUSIC_MANAGER_LOG_FILE_LEVEL", "DEBUG")),
        log_file_path=Path(os.getenv("MUSIC_MANAGER_LOG_FILE_PATH", "local/logs/backend.log")),
    )
