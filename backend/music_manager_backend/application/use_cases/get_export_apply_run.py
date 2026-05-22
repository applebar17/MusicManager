from music_manager_backend.domain.entities import ExportApplyRun
from music_manager_backend.ports.repositories import EnvironmentRepository, ExportApplyRunRepository
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class GetExportApplyRun:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        apply_runs: ExportApplyRunRepository,
    ) -> None:
        self.environments = environments
        self.apply_runs = apply_runs

    def execute(self, environment_id: str, apply_run_id: str) -> ExportApplyRun:
        if self.environments.get(environment_id) is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        apply_run = self.apply_runs.get(apply_run_id)
        if apply_run is None:
            raise NotFoundError(f"Export apply run not found: {apply_run_id}")
        if apply_run.environment_id != environment_id:
            raise ValidationError(
                f"Export apply run does not belong to environment: {apply_run_id}"
            )
        return apply_run
