from pathlib import Path

from pydantic import BaseModel


class EnvironmentCreate(BaseModel):
    name: str
    root_path: Path
    deprecated_folder_name: str = "_deprecated"


class EnvironmentUpdate(BaseModel):
    name: str | None = None
    root_path: Path | None = None
    deprecated_folder_name: str | None = None
