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


def validate_readable_file_inside_root(path: Path, root: Path) -> Path:
    root_path = root.resolve(strict=True)
    file_path = path.resolve(strict=True)
    if not file_path.is_relative_to(root_path):
        raise ValidationError(f"File path is outside environment root: {path}")
    if not file_path.is_file():
        raise ValidationError(f"Playback path is not a file: {path}")
    if not os.access(file_path, os.R_OK):
        raise ValidationError(f"Playback file is not readable: {path}")
    return file_path
