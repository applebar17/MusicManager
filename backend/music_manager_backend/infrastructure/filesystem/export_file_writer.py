import os
import shutil
from pathlib import Path
from uuid import uuid4

from music_manager_backend.domain.entities import MusicEnvironment
from music_manager_backend.domain.entities.export_plan import ExportAction, ExportPlanItem
from music_manager_backend.domain.services.export_layout import MANAGED_EXPORT_FOLDER_NAME
from music_manager_backend.shared.errors import ValidationError


class ExportFileWriter:
    def validate_plan_targets(
        self,
        *,
        environment: MusicEnvironment,
        items: tuple[ExportPlanItem, ...],
    ) -> None:
        managed_root = _managed_root(environment)
        for item in items:
            _validate_target_inside_managed_root(item.target_path, managed_root)

    def create_folder(self, environment: MusicEnvironment, target_path: Path) -> None:
        managed_root = _managed_root(environment)
        target = _validate_target_inside_managed_root(target_path, managed_root)
        if target.exists() and not target.is_dir():
            raise ValidationError(f"Export folder target is not a directory: {target_path}")
        target.mkdir(parents=True, exist_ok=True)

    def copy_file(
        self,
        *,
        environment: MusicEnvironment,
        source_path: Path | None,
        target_path: Path,
        active_source_paths: set[Path],
    ) -> None:
        source = _validate_source_file(
            environment=environment,
            source_path=source_path,
            active_source_paths=active_source_paths,
        )
        target = _validate_target_inside_managed_root(target_path, _managed_root(environment))
        if target.exists() and target.is_dir():
            raise ValidationError(f"Export copy target is a directory: {target_path}")

        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = target.with_name(f".{target.name}.tmp-{uuid4().hex}")
        try:
            shutil.copy2(source, temporary_path)
            os.replace(temporary_path, target)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def remove_stale_copy(self, environment: MusicEnvironment, target_path: Path) -> None:
        target = _validate_target_inside_managed_root(target_path, _managed_root(environment))
        if not target.exists():
            return
        if target.is_dir():
            raise ValidationError(f"Stale export target is a directory: {target_path}")
        target.unlink()

    def apply_item(
        self,
        *,
        environment: MusicEnvironment,
        item: ExportPlanItem,
        active_source_paths: set[Path],
    ) -> None:
        if item.action == ExportAction.CREATE_FOLDER:
            self.create_folder(environment, item.target_path)
            return
        if item.action in {ExportAction.COPY_FILE, ExportAction.PRESERVE_DEPRECATED}:
            self.copy_file(
                environment=environment,
                source_path=item.source_path,
                target_path=item.target_path,
                active_source_paths=active_source_paths,
            )
            return
        if item.action == ExportAction.REMOVE_STALE_COPY:
            self.remove_stale_copy(environment, item.target_path)
            return
        if item.action == ExportAction.SKIP:
            return
        raise ValidationError(f"Unsupported export action: {item.action.value}")


def _managed_root(environment: MusicEnvironment) -> Path:
    root = environment.root_path.resolve(strict=True)
    managed_root = (environment.root_path / MANAGED_EXPORT_FOLDER_NAME).resolve(strict=False)
    if not managed_root.is_relative_to(root):
        raise ValidationError("Managed export root is outside environment root")
    return managed_root


def _validate_target_inside_managed_root(target_path: Path, managed_root: Path) -> Path:
    target = target_path.resolve(strict=False)
    if not target.is_relative_to(managed_root):
        raise ValidationError(f"Export target path is outside managed export root: {target_path}")
    return target


def _validate_source_file(
    *,
    environment: MusicEnvironment,
    source_path: Path | None,
    active_source_paths: set[Path],
) -> Path:
    if source_path is None:
        raise ValidationError("Export item is missing a source path")
    planned_source = source_path.resolve(strict=False)
    if planned_source not in active_source_paths:
        raise ValidationError(
            f"Export source path is not an active matched audio file: {source_path}"
        )
    if not source_path.exists():
        raise ValidationError(f"Export source path does not exist: {source_path}")
    source = source_path.resolve(strict=True)
    environment_root = environment.root_path.resolve(strict=True)
    if not source.is_relative_to(environment_root):
        raise ValidationError(f"Export source path is outside environment root: {source_path}")
    if not source.is_file():
        raise ValidationError(f"Export source path is not a file: {source_path}")
    if not os.access(source, os.R_OK):
        raise ValidationError(f"Export source path is not readable: {source_path}")
    return source
