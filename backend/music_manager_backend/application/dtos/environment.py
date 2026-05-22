from pathlib import Path

from pydantic import BaseModel


class EnvironmentCreate(BaseModel):
    name: str
    root_path: Path
    deprecated_folder_name: str = "_deprecated"

