from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from music_manager_backend.domain.entities.export_plan import ExportAction


class ExportApplyRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_FAILURES = "completed_with_failures"
    FAILED = "failed"


class ExportApplyItemStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ExportApplyItemResult:
    action: ExportAction
    target_path: Path
    status: ExportApplyItemStatus
    export_plan_item_id: str | None = None
    source_path: Path | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class ExportApplyRun:
    id: str
    export_plan_id: str
    environment_id: str
    status: ExportApplyRunStatus
    started_at: str
    finished_at: str | None = None
    item_results: tuple[ExportApplyItemResult, ...] = field(default_factory=tuple)
