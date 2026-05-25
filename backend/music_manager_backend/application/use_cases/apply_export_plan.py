import logging

from music_manager_backend.domain.entities import (
    AudioFileStatus,
    ExportApplyItemResult,
    ExportApplyItemStatus,
    ExportApplyRun,
    ExportApplyRunStatus,
)
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.infrastructure.filesystem import ExportFileWriter, update_export_manifest
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ExportApplyRunRepository,
    ExportPlanRepository,
)
from music_manager_backend.shared.errors import MusicManagerError, NotFoundError, ValidationError
from music_manager_backend.shared.ids import new_id
from music_manager_backend.shared.time import utc_now_iso

logger = logging.getLogger(__name__)


class ApplyExportPlan:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        audio_files: AudioFileRepository,
        export_plans: ExportPlanRepository,
        apply_runs: ExportApplyRunRepository,
        writer: ExportFileWriter | None = None,
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files
        self.export_plans = export_plans
        self.apply_runs = apply_runs
        self.writer = writer or ExportFileWriter()

    def execute(self, environment_id: str, export_plan_id: str) -> ExportApplyRun:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        if environment.archived_at is not None:
            raise ValidationError(f"Environment is archived: {environment_id}")

        plan = self.export_plans.get(export_plan_id)
        if plan is None:
            raise NotFoundError(f"Export plan not found: {export_plan_id}")
        if plan.environment_id != environment_id:
            raise ValidationError(f"Export plan does not belong to environment: {export_plan_id}")

        self.writer.validate_plan_targets(environment=environment, items=plan.items)
        active_source_paths = {
            item.path.resolve(strict=False)
            for item in self.audio_files.list_by_environment(
                environment_id, status=AudioFileStatus.ACTIVE
            )
        }

        results: list[ExportApplyItemResult] = []
        manifest_add_targets = set()
        manifest_remove_targets = set()
        started_at = utc_now_iso()
        for item in plan.items:
            created_at = utc_now_iso()
            if item.action == ExportAction.SKIP:
                results.append(
                    ExportApplyItemResult(
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.SKIPPED,
                        error_code="skipped",
                        error_message=item.reason,
                        created_at=created_at,
                    )
                )
                continue
            try:
                self.writer.apply_item(
                    environment=environment,
                    item=item,
                    active_source_paths=active_source_paths,
                )
            except MusicManagerError as exc:
                results.append(
                    ExportApplyItemResult(
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.FAILED,
                        error_code=exc.code,
                        error_message=exc.message,
                        created_at=created_at,
                    )
                )
            except OSError as exc:
                results.append(
                    ExportApplyItemResult(
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.FAILED,
                        error_code="filesystem_error",
                        error_message=str(exc),
                        created_at=created_at,
                    )
                )
            else:
                if item.action in {ExportAction.COPY_FILE, ExportAction.PRESERVE_DEPRECATED}:
                    manifest_add_targets.add(item.target_path)
                elif item.action == ExportAction.REMOVE_STALE_COPY:
                    manifest_remove_targets.add(item.target_path)
                results.append(
                    ExportApplyItemResult(
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.SUCCEEDED,
                        created_at=created_at,
                    )
                )

        apply_run = ExportApplyRun(
            id=new_id("export_apply"),
            export_plan_id=export_plan_id,
            environment_id=environment_id,
            status=_run_status(results),
            started_at=started_at,
            finished_at=utc_now_iso(),
            item_results=tuple(results),
        )
        self.apply_runs.save(apply_run)
        try:
            update_export_manifest(
                root_path=environment.root_path,
                add_targets=manifest_add_targets,
                remove_targets=manifest_remove_targets,
            )
        except OSError:
            logger.warning("Failed to update export manifest", exc_info=True)
        return apply_run


def _run_status(results: list[ExportApplyItemResult]) -> ExportApplyRunStatus:
    failures = [
        item for item in results if item.status == ExportApplyItemStatus.FAILED
    ]
    if not results or len(failures) == len(results):
        return ExportApplyRunStatus.FAILED
    if failures:
        return ExportApplyRunStatus.COMPLETED_WITH_FAILURES
    return ExportApplyRunStatus.COMPLETED
