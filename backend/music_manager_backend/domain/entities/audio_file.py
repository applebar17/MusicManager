from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class AudioFileStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


@dataclass(frozen=True)
class AudioFile:
    id: str
    environment_id: str
    path: Path
    size_bytes: int
    modified_at: float
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    duration_seconds: int | None = None
    bpm: int | None = None
    key: str | None = None
    comment: str | None = None
    raw_metadata: dict[str, object] | None = None
    status: AudioFileStatus = AudioFileStatus.ACTIVE
    first_seen_scan_id: str | None = None
    last_seen_scan_id: str | None = None
    removed_at: str | None = None
