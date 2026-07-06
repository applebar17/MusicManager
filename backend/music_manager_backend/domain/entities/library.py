from dataclasses import dataclass
from pathlib import Path


DEFAULT_LIBRARY_ID = "default"


@dataclass(frozen=True)
class MusicLibrary:
    id: str
    root_path: Path
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class LibraryTrack:
    id: str
    library_id: str
    canonical_path: Path
    filename: str
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None
    normalized_title: str | None = None
    file_hash: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
