from dataclasses import replace

from music_manager_backend.application.dtos import ExportPlanUpdate
from music_manager_backend.application.use_cases.export_plan_validation import (
    validate_export_plan,
)
from music_manager_backend.domain.entities import ExportPlan
from music_manager_backend.ports.repositories import EnvironmentRepository, ExportPlanRepository
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class UpdateExportPlan:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        export_plans: ExportPlanRepository,
    ) -> None:
        self.environments = environments
        self.export_plans = export_plans

    def execute(
        self,
        environment_id: str,
        export_plan_id: str,
        data: ExportPlanUpdate,
    ) -> ExportPlan:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        plan = self.export_plans.get(export_plan_id)
        if plan is None:
            raise NotFoundError(f"Export plan not found: {export_plan_id}")
        if plan.environment_id != environment_id:
            raise ValidationError(f"Export plan does not belong to environment: {export_plan_id}")
        if plan.locked_at is not None:
            raise ValidationError(
                "Export plan is locked because apply has already started. Create a fresh preview.",
                code="export_plan_locked",
            )

        items_by_id = {item.id: item for item in plan.items}
        included_ids = data.included_item_ids
        excluded_ids = data.excluded_item_ids
        all_requested = included_ids + excluded_ids
        if len(set(all_requested)) != len(all_requested):
            raise ValidationError(
                "Export plan update contains duplicate item ids.",
                code="export_plan_duplicate_item_ids",
            )
        missing = [item_id for item_id in all_requested if item_id not in items_by_id]
        if missing:
            raise NotFoundError(f"Export plan item not found: {missing[0]}")
        expected = set(items_by_id)
        if set(all_requested) != expected:
            raise ValidationError(
                "Export plan update must include every current item as included or excluded.",
                code="export_plan_update_incomplete",
            )

        ordered_items = [
            replace(items_by_id[item_id], included=True)
            for item_id in included_ids
        ]
        ordered_items.extend(
            replace(items_by_id[item_id], included=False)
            for item_id in excluded_ids
        )
        updated_plan = validate_export_plan(
            environment,
            replace(plan, items=tuple(ordered_items)),
        )
        self.export_plans.save(updated_plan)
        return updated_plan
