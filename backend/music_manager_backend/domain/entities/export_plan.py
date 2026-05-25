from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ExportAction(StrEnum):
    CREATE_FOLDER = "create_folder"
    COPY_FILE = "copy_file"
    KEEP_EXISTING = "keep_existing"
    REMOVE_STALE_COPY = "remove_stale_copy"
    PRESERVE_DEPRECATED = "preserve_deprecated"
    SKIP = "skip"


@dataclass(frozen=True)
class ExportPlanItem:
    action: ExportAction
    target_path: Path
    source_path: Path | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ExportPlan:
    id: str
    environment_id: str
    items: tuple[ExportPlanItem, ...] = field(default_factory=tuple)

    @property
    def has_writes(self) -> bool:
        return any(
            item.action not in {ExportAction.KEEP_EXISTING, ExportAction.SKIP}
            for item in self.items
        )
