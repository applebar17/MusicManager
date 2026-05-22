import os
from pathlib import Path

from music_manager_backend.shared.errors import ValidationError


def validate_readable_directory(path: Path) -> Path:
    if not path.exists():
        raise ValidationError(f"Root path does not exist: {path}")
    if not path.is_dir():
        raise ValidationError(f"Root path is not a directory: {path}")
    if not os.access(path, os.R_OK):
        raise ValidationError(f"Root path is not readable: {path}")
    return path
