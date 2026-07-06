import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from music_manager_backend.application.dtos.library import (
    LibraryAlignmentRunRead,
    library_alignment_run_read,
)
from music_manager_backend.application.use_cases.scan_library import (
    discover_audio_files_with_metadata,
    scan_library,
)
from music_manager_backend.domain.entities import DiscoveredAudioFile
from music_manager_backend.domain.entities.library import (
    LibraryAlignmentItem,
    LibraryAlignmentItemStatus,
    LibraryAlignmentRun,
    LibraryAlignmentRunStatus,
    LibraryTrack,
    LibraryTrackStatus,
)
from music_manager_backend.domain.services.filename_sanitizer import (
    sanitize_path_part,
    unique_path,
)
from music_manager_backend.domain.services.title_normalizer import normalize_match_title
from music_manager_backend.infrastructure.filesystem.path_safety import validate_readable_directory
from music_manager_backend.ports.audio_metadata import AudioMetadataReader
from music_manager_backend.ports.filesystem import AudioFileScanner
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    LibraryAlignmentRunRepository,
    LibraryRepository,
    LibraryTrackRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError
from music_manager_backend.shared.ids import new_id
from music_manager_backend.shared.time import utc_now_iso

ScannerFactory = Callable[[Path], AudioFileScanner]


class AlignLibraryFromEnvironment:
    def __init__(
        self,
        environments: EnvironmentRepository,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
        alignment_runs: LibraryAlignmentRunRepository,
        scanner_factory: ScannerFactory,
        metadata_reader: AudioMetadataReader,
    ) -> None:
        self.environments = environments
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.alignment_runs = alignment_runs
        self.scanner_factory = scanner_factory
        self.metadata_reader = metadata_reader

    def execute(self, environment_id: str) -> LibraryAlignmentRunRead:
        library = self.libraries.get_default()
        if library is None:
            raise NotFoundError("Shared library is not configured.")
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        library_root = validate_readable_directory(library.root_path)
        environment_root = validate_readable_directory(environment.root_path)
        _reject_overlapping_roots(library_root, environment_root)

        run_id = new_id("library_alignment")
        started_at = utc_now_iso()
        scanned_library_count = scan_library(
            library_id=library.id,
            root_path=library_root,
            library_tracks=self.library_tracks,
            metadata_reader=self.metadata_reader,
        )
        usb_files = discover_audio_files_with_metadata(
            environment_root,
            self.scanner_factory,
            self.metadata_reader,
        )
        items: list[LibraryAlignmentItem] = []
        counts = _Counts()
        used_paths = _existing_library_paths(library_root)
        active_tracks = self.library_tracks.list_by_status(library.id, LibraryTrackStatus.ACTIVE)
        identity_map = _identity_map(active_tracks)

        for usb_file in usb_files:
            item = self._align_file(
                run_id=run_id,
                library_id=library.id,
                library_root=library_root,
                usb_file=usb_file,
                identity_map=identity_map,
                used_paths=used_paths,
            )
            items.append(item)
            counts.add(item.status)

        status = (
            LibraryAlignmentRunStatus.COMPLETED_WITH_ISSUES
            if counts.has_issues
            else LibraryAlignmentRunStatus.COMPLETED
        )
        run = LibraryAlignmentRun(
            id=run_id,
            library_id=library.id,
            environment_id=environment_id,
            status=status,
            started_at=started_at,
            finished_at=utc_now_iso(),
            scanned_library_count=scanned_library_count,
            scanned_usb_count=len(usb_files),
            copied_count=counts.copied,
            reused_count=counts.reused,
            updated_count=counts.updated,
            skipped_collision_count=counts.skipped_collision,
            skipped_error_count=counts.skipped_error,
            warning_count=counts.warning,
        )
        item_tuple = tuple(items)
        self.alignment_runs.save(run, item_tuple)
        return library_alignment_run_read(run, item_tuple)

    def _align_file(
        self,
        *,
        run_id: str,
        library_id: str,
        library_root: Path,
        usb_file: DiscoveredAudioFile,
        identity_map: dict[tuple[str, int], list[LibraryTrack]],
        used_paths: set[Path],
    ) -> LibraryAlignmentItem:
        title = usb_file.title or usb_file.path.stem
        normalized_title = normalize_match_title(title)
        matches = (
            identity_map.get((normalized_title, usb_file.duration_seconds), [])
            if usb_file.duration_seconds is not None
            else []
        )
        if len(matches) == 1:
            return _item(
                run_id=run_id,
                status=LibraryAlignmentItemStatus.REUSED,
                source=usb_file,
                normalized_title=normalized_title,
                target_path=matches[0].canonical_path,
                library_track_id=matches[0].id,
            )
        if len(matches) > 1:
            return _item(
                run_id=run_id,
                status=LibraryAlignmentItemStatus.SKIPPED_COLLISION,
                source=usb_file,
                normalized_title=normalized_title,
                reason_code="identity_collision",
                reason_message="Multiple active library tracks match this title and duration.",
            )

        target_path = _target_path(library_root, usb_file.path, used_paths)
        try:
            shutil.copy2(usb_file.path, target_path)
            stat = target_path.stat()
        except OSError as exc:
            return _item(
                run_id=run_id,
                status=LibraryAlignmentItemStatus.SKIPPED_ERROR,
                source=usb_file,
                normalized_title=normalized_title,
                target_path=target_path,
                reason_code="copy_failed",
                reason_message=str(exc),
            )

        now = utc_now_iso()
        existing_target = self.library_tracks.get_by_canonical_path(library_id, target_path)
        track = LibraryTrack(
            id=existing_target.id if existing_target is not None else new_id("library_track"),
            library_id=library_id,
            canonical_path=target_path,
            filename=target_path.name,
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
            status=LibraryTrackStatus.ACTIVE,
            title=usb_file.title,
            artist=usb_file.artist,
            duration_seconds=usb_file.duration_seconds,
            normalized_title=normalized_title,
            file_hash=existing_target.file_hash if existing_target is not None else None,
            created_at=existing_target.created_at if existing_target is not None else now,
            updated_at=now,
            first_seen_at=existing_target.first_seen_at if existing_target is not None else now,
            last_seen_at=now,
            missing_at=None,
        )
        self.library_tracks.save(track)
        status = (
            LibraryAlignmentItemStatus.WARNING_IDENTITY_INCOMPLETE
            if usb_file.duration_seconds is None
            else LibraryAlignmentItemStatus.COPIED
        )
        return _item(
            run_id=run_id,
            status=status,
            source=usb_file,
            normalized_title=normalized_title,
            target_path=target_path,
            library_track_id=track.id,
            reason_code="identity_incomplete" if usb_file.duration_seconds is None else None,
            reason_message=(
                "Copied, but duration metadata is missing so automatic identity matching is incomplete."
                if usb_file.duration_seconds is None
                else None
            ),
        )


class GetLatestLibraryAlignmentRun:
    def __init__(
        self,
        libraries: LibraryRepository,
        alignment_runs: LibraryAlignmentRunRepository,
    ) -> None:
        self.libraries = libraries
        self.alignment_runs = alignment_runs

    def execute(self) -> LibraryAlignmentRunRead | None:
        library = self.libraries.get_default()
        if library is None:
            return None
        latest = self.alignment_runs.latest(library.id)
        if latest is None:
            return None
        run, items = latest
        return library_alignment_run_read(run, items)


@dataclass
class _Counts:
    copied: int = 0
    reused: int = 0
    updated: int = 0
    skipped_collision: int = 0
    skipped_error: int = 0
    warning: int = 0

    @property
    def has_issues(self) -> bool:
        return self.skipped_collision > 0 or self.skipped_error > 0 or self.warning > 0

    def add(self, status: LibraryAlignmentItemStatus) -> None:
        if status == LibraryAlignmentItemStatus.COPIED:
            self.copied += 1
        elif status == LibraryAlignmentItemStatus.REUSED:
            self.reused += 1
        elif status == LibraryAlignmentItemStatus.UPDATED:
            self.updated += 1
        elif status == LibraryAlignmentItemStatus.SKIPPED_COLLISION:
            self.skipped_collision += 1
        elif status == LibraryAlignmentItemStatus.SKIPPED_ERROR:
            self.skipped_error += 1
        elif status == LibraryAlignmentItemStatus.WARNING_IDENTITY_INCOMPLETE:
            self.copied += 1
            self.warning += 1


def _reject_overlapping_roots(library_root: Path, environment_root: Path) -> None:
    library_resolved = library_root.resolve(strict=True)
    environment_resolved = environment_root.resolve(strict=True)
    if library_resolved == environment_resolved:
        raise ValidationError("Library root and environment root must be different folders.")
    if library_resolved.is_relative_to(environment_resolved):
        raise ValidationError("Library root cannot be inside the environment root.")
    if environment_resolved.is_relative_to(library_resolved):
        raise ValidationError("Environment root cannot be inside the library root.")


def _existing_library_paths(library_root: Path) -> set[Path]:
    return {
        item
        for item in library_root.iterdir()
        if item.is_file()
    }


def _identity_map(tracks: list[LibraryTrack]) -> dict[tuple[str, int], list[LibraryTrack]]:
    grouped: dict[tuple[str, int], list[LibraryTrack]] = {}
    for track in tracks:
        if track.normalized_title is None or track.duration_seconds is None:
            continue
        grouped.setdefault((track.normalized_title, track.duration_seconds), []).append(track)
    return grouped


def _target_path(library_root: Path, source_path: Path, used_paths: set[Path]) -> Path:
    filename = f"{sanitize_path_part(source_path.stem)}{source_path.suffix}"
    return unique_path(library_root / filename, used_paths)


def _item(
    *,
    run_id: str,
    status: LibraryAlignmentItemStatus,
    source: DiscoveredAudioFile,
    normalized_title: str,
    target_path: Path | None = None,
    library_track_id: str | None = None,
    reason_code: str | None = None,
    reason_message: str | None = None,
) -> LibraryAlignmentItem:
    return LibraryAlignmentItem(
        id=new_id("library_alignment_item"),
        run_id=run_id,
        status=status,
        source_path=source.path,
        target_path=target_path,
        library_track_id=library_track_id,
        reason_code=reason_code,
        reason_message=reason_message,
        title=source.title,
        artist=source.artist,
        duration_seconds=source.duration_seconds,
        normalized_title=normalized_title,
    )
