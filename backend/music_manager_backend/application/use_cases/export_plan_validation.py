from dataclasses import replace
from pathlib import Path

from music_manager_backend.domain.entities import ExportPlan, ExportPlanItem, MusicEnvironment
from music_manager_backend.domain.entities.export_plan import ExportAction


def validate_export_plan(environment: MusicEnvironment, plan: ExportPlan) -> ExportPlan:
    _ = environment
    item_errors: dict[str, tuple[str, str]] = {}
    included_positions = {
        item.id: position for position, item in enumerate(plan.items) if item.included
    }
    all_folder_items = {
        item.target_path.resolve(strict=False): item
        for item in plan.items
        if item.action == ExportAction.CREATE_FOLDER
    }

    for item in plan.items:
        if not item.included:
            continue
        if item.action == ExportAction.CREATE_FOLDER:
            parent = item.target_path.parent.resolve(strict=False)
            parent_item = all_folder_items.get(parent)
            if parent_item is not None:
                _require_before(
                    item_errors=item_errors,
                    dependency=parent_item,
                    item=item,
                    included_positions=included_positions,
                    message=(
                        f"Create {parent_item.target_path} before creating "
                        f"{item.target_path}."
                    ),
                )
            continue

        required_folder = _required_created_folder(item)
        if required_folder is not None:
            folder_item = all_folder_items.get(required_folder.resolve(strict=False))
            if folder_item is not None:
                _require_before(
                    item_errors=item_errors,
                    dependency=folder_item,
                    item=item,
                    included_positions=included_positions,
                    message=(
                        f"Create {folder_item.target_path} before applying this action."
                    ),
                )

    preservation_dependencies = _preservation_dependencies(plan.items)
    for item in plan.items:
        if not item.included or item.action != ExportAction.REMOVE_STALE_COPY:
            continue
        for dependency in preservation_dependencies.get(
            item.target_path.resolve(strict=False), []
        ):
            _require_before(
                item_errors=item_errors,
                dependency=dependency,
                item=item,
                included_positions=included_positions,
                message=(
                    "Preserve or copy this file before removing the stale playlist copy."
                ),
            )

    next_items = tuple(
        replace(
            item,
            validation_error_code=item_errors.get(item.id, (None, None))[0],
            validation_error_message=item_errors.get(item.id, (None, None))[1],
        )
        for item in plan.items
    )
    has_errors = bool(item_errors)
    return replace(
        plan,
        items=next_items,
        validation_error_code="invalid_export_plan" if has_errors else None,
        validation_error_message=(
            "Fix export plan validation errors before applying."
            if has_errors
            else None
        ),
    )


def _required_created_folder(item: ExportPlanItem) -> Path | None:
    if item.action in {ExportAction.COPY_FILE, ExportAction.PRESERVE_DEPRECATED}:
        return item.target_path.parent
    return None


def _preservation_dependencies(
    items: tuple[ExportPlanItem, ...],
) -> dict[Path, list[ExportPlanItem]]:
    dependencies: dict[Path, list[ExportPlanItem]] = {}
    for item in items:
        if item.action not in {ExportAction.COPY_FILE, ExportAction.PRESERVE_DEPRECATED}:
            continue
        if item.source_path is None:
            continue
        dependencies.setdefault(item.source_path.resolve(strict=False), []).append(item)
    return dependencies


def _require_before(
    *,
    item_errors: dict[str, tuple[str, str]],
    dependency: ExportPlanItem,
    item: ExportPlanItem,
    included_positions: dict[str, int],
    message: str,
) -> None:
    dependency_position = included_positions.get(dependency.id)
    item_position = included_positions.get(item.id)
    if (
        dependency_position is not None
        and item_position is not None
        and dependency_position < item_position
    ):
        return
    item_errors.setdefault(item.id, ("export_plan_dependency_order", message))
