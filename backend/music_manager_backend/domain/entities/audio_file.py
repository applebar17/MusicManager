from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioFile:
    id: str
    environment_id: str
    path: Path
    size_bytes: int
    modified_at: float
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None

