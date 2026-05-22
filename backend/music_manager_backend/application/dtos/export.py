from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from music_manager_backend.domain.entities import ExportPlan


class ExportPlanCreate(BaseModel):
    playlist_ids: list[str] | None = None


class ExportPlanItemRead(BaseModel):
    action: str
    target_path: str
    source_path: str | None = None
    reason: str | None = None


class ExportPlanRead(BaseModel):
    export_plan_id: str
    environment_id: str
    counts: dict[str, int]
    items: list[ExportPlanItemRead]


def export_plan_read(export_plan: ExportPlan) -> ExportPlanRead:
    counts = Counter(item.action.value for item in export_plan.items)
    return ExportPlanRead(
        export_plan_id=export_plan.id,
        environment_id=export_plan.environment_id,
        counts=dict(counts),
        items=[
            ExportPlanItemRead(
                action=item.action.value,
                target_path=_path_to_string(item.target_path),
                source_path=_path_to_string(item.source_path) if item.source_path else None,
                reason=item.reason,
            )
            for item in export_plan.items
        ],
    )


def _path_to_string(path: Path) -> str:
    return str(path)
