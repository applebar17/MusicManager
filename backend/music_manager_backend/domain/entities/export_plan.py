from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from music_manager_backend.shared.ids import new_id


class ExportAction(StrEnum):
    CREATE_FOLDER = "create_folder"
    COPY_FILE = "copy_file"
    KEEP_EXISTING = "keep_existing"
    REMOVE_DUPLICATE_COPY = "remove_duplicate_copy"
    REMOVE_STALE_COPY = "remove_stale_copy"
    PRESERVE_DEPRECATED = "preserve_deprecated"
    SKIP = "skip"


@dataclass(frozen=True)
class ExportPlanItem:
    action: ExportAction
    target_path: Path
    source_path: Path | None = None
    reason: str | None = None
    id: str = field(default_factory=lambda: new_id("export_plan_item"))
    included: bool = True
    validation_error_code: str | None = None
    validation_error_message: str | None = None


@dataclass(frozen=True)
class ExportPlan:
    id: str
    environment_id: str
    items: tuple[ExportPlanItem, ...] = field(default_factory=tuple)
    locked_at: str | None = None
    validation_error_code: str | None = None
    validation_error_message: str | None = None

    @property
    def has_writes(self) -> bool:
        return any(
            item.action not in {ExportAction.KEEP_EXISTING, ExportAction.SKIP}
            for item in self.included_items
        )

    @property
    def included_items(self) -> tuple[ExportPlanItem, ...]:
        return tuple(item for item in self.items if item.included)

    @property
    def is_valid(self) -> bool:
        return self.validation_error_code is None and all(
            item.validation_error_code is None for item in self.items
        )
