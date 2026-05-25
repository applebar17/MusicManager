import os
import shutil
from pathlib import Path
from uuid import uuid4

from music_manager_backend.domain.entities import MusicEnvironment
from music_manager_backend.domain.entities.export_plan import ExportAction, ExportPlanItem
from music_manager_backend.domain.services.export_layout import ExportLayout
from music_manager_backend.infrastructure.filesystem.export_manifest import read_export_manifest
from music_manager_backend.shared.errors import ValidationError


class ExportFileWriter:
    def validate_plan_targets(
        self,
        *,
        environment: MusicEnvironment,
        items: tuple[ExportPlanItem, ...],
    ) -> None:
        for item in items:
            _validate_plan_item_target(environment, item)

    def create_folder(self, environment: MusicEnvironment, target_path: Path) -> None:
        target = _validate_target_inside_export_root(
            environment,
            target_path,
            allow_metadata=True,
        )
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
        allow_metadata: bool = False,
    ) -> None:
        source = _validate_source_file(
            environment=environment,
            source_path=source_path,
            active_source_paths=active_source_paths,
        )
        target = _validate_target_inside_export_root(
            environment,
            target_path,
            allow_metadata=allow_metadata,
        )
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
        target = _validate_target_inside_export_root(
            environment,
            target_path,
            allow_metadata=False,
        )
        if not target.exists():
            return
        manifest = read_export_manifest(environment.root_path)
        if target.resolve(strict=False) not in manifest.targets:
            raise ValidationError(f"Stale export target is not app-owned: {target_path}")
        if target.is_dir():
            raise ValidationError(f"Stale export target is a directory: {target_path}")
        target.unlink()

    def keep_existing(self, environment: MusicEnvironment, target_path: Path) -> None:
        target = _validate_target_inside_export_root(
            environment,
            target_path,
            allow_metadata=True,
        )
        if not target.exists():
            raise ValidationError(f"Existing export target no longer exists: {target_path}")
        if not target.is_file():
            raise ValidationError(f"Existing export target is not a file: {target_path}")

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
                allow_metadata=item.action == ExportAction.PRESERVE_DEPRECATED,
            )
            return
        if item.action == ExportAction.REMOVE_STALE_COPY:
            self.remove_stale_copy(environment, item.target_path)
            return
        if item.action == ExportAction.KEEP_EXISTING:
            self.keep_existing(environment, item.target_path)
            return
        if item.action == ExportAction.SKIP:
            return
        raise ValidationError(f"Unsupported export action: {item.action.value}")


def _export_root(environment: MusicEnvironment) -> Path:
    root = environment.root_path.resolve(strict=True)
    return root


def _validate_plan_item_target(environment: MusicEnvironment, item: ExportPlanItem) -> Path:
    if item.action == ExportAction.CREATE_FOLDER:
        return _validate_target_inside_export_root(
            environment,
            item.target_path,
            allow_metadata=True,
        )
    if item.action == ExportAction.PRESERVE_DEPRECATED:
        return _validate_deprecated_target(environment, item.target_path)
    if item.action == ExportAction.KEEP_EXISTING:
        return _validate_target_inside_export_root(
            environment,
            item.target_path,
            allow_metadata=True,
        )
    return _validate_target_inside_export_root(
        environment,
        item.target_path,
        allow_metadata=False,
    )


def _validate_deprecated_target(environment: MusicEnvironment, target_path: Path) -> Path:
    target = _validate_target_inside_export_root(
        environment,
        target_path,
        allow_metadata=True,
    )
    deprecated_root = ExportLayout(environment).deprecated_folder.resolve(strict=False)
    if not target.is_relative_to(deprecated_root):
        raise ValidationError(f"Deprecated export target is outside metadata folder: {target_path}")
    return target


def _validate_target_inside_export_root(
    environment: MusicEnvironment,
    target_path: Path,
    *,
    allow_metadata: bool,
) -> Path:
    target = target_path.resolve(strict=False)
    export_root = _export_root(environment)
    if not target.is_relative_to(export_root):
        raise ValidationError(f"Export target path is outside environment root: {target_path}")
    metadata_root = ExportLayout(environment).metadata_root.resolve(strict=False)
    if not allow_metadata and target.is_relative_to(metadata_root):
        raise ValidationError(f"Export target path is inside app metadata folder: {target_path}")
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
