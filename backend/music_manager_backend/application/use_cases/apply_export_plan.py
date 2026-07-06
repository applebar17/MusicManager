import logging
from dataclasses import replace
from pathlib import Path

from music_manager_backend.domain.entities import (
    AudioFileStatus,
    ExportApplyItemResult,
    ExportApplyItemStatus,
    ExportApplyRun,
    ExportApplyRunStatus,
    ExportPlanItem,
    LibraryTrackStatus,
)
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.infrastructure.filesystem import (
    ExportFileWriter,
    update_export_manifest,
)
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ExportApplyRunRepository,
    ExportPlanRepository,
    LibraryRepository,
    LibraryTrackRepository,
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
        libraries: LibraryRepository | None = None,
        library_tracks: LibraryTrackRepository | None = None,
        writer: ExportFileWriter | None = None,
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files
        self.export_plans = export_plans
        self.apply_runs = apply_runs
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.writer = writer or ExportFileWriter()

    def execute(self, environment_id: str, export_plan_id: str) -> ExportApplyRun:
        apply_run = self.start(environment_id, export_plan_id)
        return self.run(apply_run.id)

    def start(self, environment_id: str, export_plan_id: str) -> ExportApplyRun:
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
        if plan.locked_at is not None:
            raise ValidationError(
                "Export plan is locked because apply has already started. Create a fresh preview.",
                code="export_plan_locked",
            )
        if not plan.is_valid:
            raise ValidationError(
                plan.validation_error_message
                or "Fix export plan validation errors before applying.",
                code=plan.validation_error_code or "invalid_export_plan",
            )

        self.writer.validate_plan_targets(environment=environment, items=plan.included_items)
        locked_at = utc_now_iso()
        self.export_plans.save(replace(plan, locked_at=locked_at))
        apply_run = ExportApplyRun(
            id=new_id("export_apply"),
            export_plan_id=export_plan_id,
            environment_id=environment_id,
            status=ExportApplyRunStatus.QUEUED,
            started_at=locked_at,
            item_results=tuple(_pending_result(item, locked_at) for item in plan.included_items),
        )
        self.apply_runs.save(apply_run)
        return apply_run

    def run(self, apply_run_id: str) -> ExportApplyRun:
        apply_run = self.apply_runs.get(apply_run_id)
        if apply_run is None:
            raise NotFoundError(f"Export apply run not found: {apply_run_id}")
        environment = self.environments.get(apply_run.environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {apply_run.environment_id}")
        plan = self.export_plans.get(apply_run.export_plan_id)
        if plan is None:
            raise NotFoundError(f"Export plan not found: {apply_run.export_plan_id}")

        active_source_paths = {
            item.path.resolve(strict=False)
            for item in self.audio_files.list_by_environment(
                apply_run.environment_id, status=AudioFileStatus.ACTIVE
            )
        }
        active_source_paths.update(self._active_library_source_paths())

        results: list[ExportApplyItemResult] = list(apply_run.item_results)
        manifest_add_targets = set()
        manifest_remove_targets = set()
        failed_source_paths: set[Path] = set()
        running_run = replace(apply_run, status=ExportApplyRunStatus.RUNNING)
        self.apply_runs.save(running_run)
        for index, item in enumerate(plan.included_items):
            created_at = utc_now_iso()
            results[index] = _running_result(item, created_at)
            self.apply_runs.save(
                replace(
                    running_run,
                    item_results=tuple(results),
                )
            )
            if item.action == ExportAction.SKIP:
                results[index] = (
                    ExportApplyItemResult(
                        export_plan_item_id=item.id,
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.SKIPPED,
                        error_code="skipped",
                        error_message=item.reason,
                        created_at=created_at,
                    )
                )
                self.apply_runs.save(replace(running_run, item_results=tuple(results)))
                continue
            if (
                item.action == ExportAction.REMOVE_STALE_COPY
                and item.target_path.resolve(strict=False) in failed_source_paths
            ):
                results[index] = (
                    ExportApplyItemResult(
                        export_plan_item_id=item.id,
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.FAILED,
                        error_code="stale_removal_blocked",
                        error_message=(
                            "Stale removal blocked because preserving or copying this "
                            "source file failed earlier in the export plan."
                        ),
                        created_at=created_at,
                    )
                )
                self.apply_runs.save(replace(running_run, item_results=tuple(results)))
                continue
            try:
                self.writer.apply_item(
                    environment=environment,
                    item=item,
                    active_source_paths=active_source_paths,
                )
            except MusicManagerError as exc:
                results[index] = (
                    ExportApplyItemResult(
                        export_plan_item_id=item.id,
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.FAILED,
                        error_code=exc.code,
                        error_message=exc.message,
                        created_at=created_at,
                    )
                )
                _record_failed_source(item, failed_source_paths)
            except OSError as exc:
                results[index] = (
                    ExportApplyItemResult(
                        export_plan_item_id=item.id,
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.FAILED,
                        error_code="filesystem_error",
                        error_message=str(exc),
                        created_at=created_at,
                    )
                )
                _record_failed_source(item, failed_source_paths)
            else:
                if item.action in {
                    ExportAction.COPY_FILE,
                    ExportAction.PRESERVE_DEPRECATED,
                    ExportAction.WRITE_TRACKS_JSON,
                }:
                    manifest_add_targets.add(item.target_path)
                elif item.action in {
                    ExportAction.REMOVE_DUPLICATE_COPY,
                    ExportAction.REMOVE_STALE_COPY,
                }:
                    manifest_remove_targets.add(item.target_path)
                results[index] = (
                    ExportApplyItemResult(
                        export_plan_item_id=item.id,
                        action=item.action,
                        source_path=item.source_path,
                        target_path=item.target_path,
                        status=ExportApplyItemStatus.SUCCEEDED,
                        created_at=created_at,
                    )
                )
            self.apply_runs.save(replace(running_run, item_results=tuple(results)))

        apply_run = ExportApplyRun(
            id=apply_run_id,
            export_plan_id=plan.id,
            environment_id=environment.id,
            status=_run_status(results),
            started_at=running_run.started_at,
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

    def _active_library_source_paths(self) -> set[Path]:
        if self.libraries is None or self.library_tracks is None:
            return set()
        library = self.libraries.get_default()
        if library is None:
            return set()
        return {
            item.canonical_path.resolve(strict=False)
            for item in self.library_tracks.list_by_status(
                library.id,
                LibraryTrackStatus.ACTIVE,
            )
        }


def _run_status(results: list[ExportApplyItemResult]) -> ExportApplyRunStatus:
    failures = [
        item for item in results if item.status == ExportApplyItemStatus.FAILED
    ]
    if not results or len(failures) == len(results):
        return ExportApplyRunStatus.FAILED
    if failures:
        return ExportApplyRunStatus.COMPLETED_WITH_FAILURES
    return ExportApplyRunStatus.COMPLETED


def _pending_result(item: ExportPlanItem, created_at: str) -> ExportApplyItemResult:
    return ExportApplyItemResult(
        export_plan_item_id=item.id,
        action=item.action,
        source_path=item.source_path,
        target_path=item.target_path,
        status=ExportApplyItemStatus.PENDING,
        created_at=created_at,
    )


def _running_result(item: ExportPlanItem, created_at: str) -> ExportApplyItemResult:
    return ExportApplyItemResult(
        export_plan_item_id=item.id,
        action=item.action,
        source_path=item.source_path,
        target_path=item.target_path,
        status=ExportApplyItemStatus.RUNNING,
        created_at=created_at,
    )


def _record_failed_source(item: ExportPlanItem, failed_source_paths: set[Path]) -> None:
    if item.action not in {ExportAction.COPY_FILE, ExportAction.PRESERVE_DEPRECATED}:
        return
    if item.source_path is None:
        return
    failed_source_paths.add(item.source_path.resolve(strict=False))
