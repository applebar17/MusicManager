from music_manager_backend.domain.entities import ExportPlan
from music_manager_backend.ports.repositories import EnvironmentRepository, ExportPlanRepository
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class ListExportPlan:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        export_plans: ExportPlanRepository,
    ) -> None:
        self.environments = environments
        self.export_plans = export_plans

    def execute(self, environment_id: str, export_plan_id: str) -> ExportPlan:
        if self.environments.get(environment_id) is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        export_plan = self.export_plans.get(export_plan_id)
        if export_plan is None:
            raise NotFoundError(f"Export plan not found: {export_plan_id}")
        if export_plan.environment_id != environment_id:
            raise ValidationError(f"Export plan does not belong to environment: {export_plan_id}")
        return export_plan
