from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveredAudioFile:
    path: Path
    size_bytes: int
    modified_at: float
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None
