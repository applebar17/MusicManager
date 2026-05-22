from dataclasses import dataclass, field

from music_manager_backend.shared.time import utc_now_iso


@dataclass(frozen=True)
class ScanRun:
    id: str
    environment_id: str
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None
    added_count: int = 0
    changed_count: int = 0
    removed_count: int = 0
    moved_count: int = 0
    unchanged_count: int = 0
    total_active_count: int = 0


@dataclass(frozen=True)
class ScanSummary:
    scan_run_id: str
    environment_id: str
    added: int
    changed: int
    removed: int
    moved: int
    unchanged: int
    total_active: int
