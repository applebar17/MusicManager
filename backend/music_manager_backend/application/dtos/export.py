from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from music_manager_backend.domain.entities import ExportApplyRun, ExportPlan


class ExportPlanCreate(BaseModel):
    playlist_ids: list[str] | None = None


class ExportPlanUpdate(BaseModel):
    included_item_ids: list[str]
    excluded_item_ids: list[str]


class ExportPlanValidationErrorRead(BaseModel):
    export_plan_item_id: str | None = None
    code: str
    message: str


class ExportPlanItemRead(BaseModel):
    export_plan_item_id: str
    position: int
    action: str
    target_path: str
    source_path: str | None = None
    reason: str | None = None
    included: bool
    validation_error_code: str | None = None
    validation_error_message: str | None = None


class ExportPlanRead(BaseModel):
    export_plan_id: str
    environment_id: str
    locked_at: str | None = None
    is_valid: bool
    validation_error_code: str | None = None
    validation_error_message: str | None = None
    validation_errors: list[ExportPlanValidationErrorRead]
    counts: dict[str, int]
    items: list[ExportPlanItemRead]


class ExportApplyItemResultRead(BaseModel):
    export_plan_item_id: str | None = None
    action: str
    target_path: str
    status: str
    source_path: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str | None = None


class ExportApplyRunRead(BaseModel):
    apply_run_id: str
    export_plan_id: str
    environment_id: str
    status: str
    counts: dict[str, int]
    item_results: list[ExportApplyItemResultRead]


def export_plan_read(export_plan: ExportPlan) -> ExportPlanRead:
    counts = Counter(item.action.value for item in export_plan.included_items)
    validation_errors = []
    if (
        export_plan.validation_error_code is not None
        and export_plan.validation_error_message is not None
    ):
        validation_errors.append(
            ExportPlanValidationErrorRead(
                code=export_plan.validation_error_code,
                message=export_plan.validation_error_message,
            )
        )
    validation_errors.extend(
        ExportPlanValidationErrorRead(
            export_plan_item_id=item.id,
            code=item.validation_error_code,
            message=item.validation_error_message,
        )
        for item in export_plan.items
        if item.validation_error_code is not None and item.validation_error_message is not None
    )
    return ExportPlanRead(
        export_plan_id=export_plan.id,
        environment_id=export_plan.environment_id,
        locked_at=export_plan.locked_at,
        is_valid=export_plan.is_valid,
        validation_error_code=export_plan.validation_error_code,
        validation_error_message=export_plan.validation_error_message,
        validation_errors=validation_errors,
        counts=dict(counts),
        items=[
            ExportPlanItemRead(
                export_plan_item_id=item.id,
                position=position,
                action=item.action.value,
                target_path=_path_to_string(item.target_path),
                source_path=_path_to_string(item.source_path) if item.source_path else None,
                reason=item.reason,
                included=item.included,
                validation_error_code=item.validation_error_code,
                validation_error_message=item.validation_error_message,
            )
            for position, item in enumerate(export_plan.items)
        ],
    )


def export_apply_run_read(apply_run: ExportApplyRun) -> ExportApplyRunRead:
    counts = Counter(item.status.value for item in apply_run.item_results)
    return ExportApplyRunRead(
        apply_run_id=apply_run.id,
        export_plan_id=apply_run.export_plan_id,
        environment_id=apply_run.environment_id,
        status=apply_run.status.value,
        counts=dict(counts),
        item_results=[
            ExportApplyItemResultRead(
                export_plan_item_id=item.export_plan_item_id,
                action=item.action.value,
                target_path=_path_to_string(item.target_path),
                status=item.status.value,
                source_path=_path_to_string(item.source_path) if item.source_path else None,
                error_code=item.error_code,
                error_message=item.error_message,
                created_at=item.created_at,
            )
            for item in apply_run.item_results
        ],
    )


def _path_to_string(path: Path) -> str:
    return str(path)
