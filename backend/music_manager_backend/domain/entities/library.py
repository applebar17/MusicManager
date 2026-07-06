from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


DEFAULT_LIBRARY_ID = "default"


class LibraryTrackStatus(StrEnum):
    ACTIVE = "active"
    MISSING = "missing"


class LibraryAlignmentRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_ISSUES = "completed_with_issues"
    FAILED = "failed"


class LibraryAlignmentItemStatus(StrEnum):
    COPIED = "copied"
    REUSED = "reused"
    UPDATED = "updated"
    SKIPPED_COLLISION = "skipped_collision"
    SKIPPED_ERROR = "skipped_error"
    WARNING_IDENTITY_INCOMPLETE = "warning_identity_incomplete"


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
    size_bytes: int = 0
    modified_at: float = 0.0
    status: LibraryTrackStatus = LibraryTrackStatus.ACTIVE
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None
    normalized_title: str | None = None
    file_hash: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    missing_at: str | None = None


@dataclass(frozen=True)
class LibraryAlignmentRun:
    id: str
    library_id: str
    environment_id: str
    status: LibraryAlignmentRunStatus
    started_at: str
    finished_at: str | None = None
    scanned_library_count: int = 0
    scanned_usb_count: int = 0
    copied_count: int = 0
    reused_count: int = 0
    updated_count: int = 0
    skipped_collision_count: int = 0
    skipped_error_count: int = 0
    warning_count: int = 0


@dataclass(frozen=True)
class LibraryAlignmentItem:
    id: str
    run_id: str
    status: LibraryAlignmentItemStatus
    source_path: Path
    target_path: Path | None = None
    library_track_id: str | None = None
    reason_code: str | None = None
    reason_message: str | None = None
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None
    normalized_title: str | None = None
