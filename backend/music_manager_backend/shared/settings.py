from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    database_path: Path = Path("music-manager.sqlite3")

