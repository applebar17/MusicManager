from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from music_manager_backend.domain.entities import (
    AudioFile,
    AudioMetadata,
    DiscoveredAudioFile,
    ScanRun,
    ScanSummary,
)
from music_manager_backend.domain.entities.audio_file import AudioFileStatus
from music_manager_backend.ports.audio_metadata import AudioMetadataReader
from music_manager_backend.ports.filesystem import AudioFileScanner
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ScanRunRepository,
)
from music_manager_backend.shared.errors import NotFoundError
from music_manager_backend.shared.ids import new_id
from music_manager_backend.shared.time import utc_now_iso

ScannerFactory = Callable[[Path], AudioFileScanner]


class ScanEnvironment:
    def __init__(
        self,
        environments: EnvironmentRepository,
        audio_files: AudioFileRepository,
        scan_runs: ScanRunRepository,
        scanner_factory: ScannerFactory,
        metadata_reader: AudioMetadataReader,
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files
        self.scan_runs = scan_runs
        self.scanner_factory = scanner_factory
        self.metadata_reader = metadata_reader

    def execute(self, environment_id: str) -> ScanSummary:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        scan_id = new_id("scan")
        started_at = utc_now_iso()
        scanner = self.scanner_factory(environment.root_path)
        discovered = [
            _with_metadata(item, self.metadata_reader.read(item.path))
            for item in scanner.scan()
        ]
        active_files = self.audio_files.list_by_environment(
            environment_id,
            status=AudioFileStatus.ACTIVE,
        )

        counts = _ScanCounts()
        discovered_by_path = {item.path: item for item in discovered}
        active_by_path = {item.path: item for item in active_files}
        missing_active = [item for item in active_files if item.path not in discovered_by_path]
        moved_old_ids: set[str] = set()
        moved_new_paths: set[Path] = set()

        for discovered_file in discovered:
            existing = active_by_path.get(discovered_file.path)
            if existing is None:
                moved = _pop_moved_candidate(discovered_file, missing_active, moved_old_ids)
                if moved is None:
                    self.audio_files.save(_new_audio_file(environment_id, scan_id, discovered_file))
                    counts.added += 1
                else:
                    self.audio_files.save(
                        _seen_audio_file(moved, scan_id, discovered_file, refresh_metadata=True)
                    )
                    moved_old_ids.add(moved.id)
                    moved_new_paths.add(discovered_file.path)
                    counts.moved += 1
                continue

            if _same_file_state(existing, discovered_file):
                self.audio_files.save(
                    _seen_audio_file(existing, scan_id, discovered_file, refresh_metadata=False)
                )
                counts.unchanged += 1
            else:
                self.audio_files.save(
                    _seen_audio_file(existing, scan_id, discovered_file, refresh_metadata=True)
                )
                counts.changed += 1

        removed_at = utc_now_iso()
        for missing in missing_active:
            if missing.id in moved_old_ids or missing.path in moved_new_paths:
                continue
            self.audio_files.save(_removed_audio_file(missing, removed_at))
            counts.removed += 1

        total_active = len(
            self.audio_files.list_by_environment(environment_id, status=AudioFileStatus.ACTIVE)
        )
        finished_at = utc_now_iso()
        scan_run = ScanRun(
            id=scan_id,
            environment_id=environment_id,
            started_at=started_at,
            finished_at=finished_at,
            added_count=counts.added,
            changed_count=counts.changed,
            removed_count=counts.removed,
            moved_count=counts.moved,
            unchanged_count=counts.unchanged,
            total_active_count=total_active,
        )
        self.scan_runs.save(scan_run)
        return ScanSummary(
            scan_run_id=scan_id,
            environment_id=environment_id,
            added=counts.added,
            changed=counts.changed,
            removed=counts.removed,
            moved=counts.moved,
            unchanged=counts.unchanged,
            total_active=total_active,
        )


class _ScanCounts:
    def __init__(self) -> None:
        self.added = 0
        self.changed = 0
        self.removed = 0
        self.moved = 0
        self.unchanged = 0


def _new_audio_file(
    environment_id: str,
    scan_id: str,
    discovered_file: DiscoveredAudioFile,
) -> AudioFile:
    return AudioFile(
        id=new_id("file"),
        environment_id=environment_id,
        path=discovered_file.path,
        size_bytes=discovered_file.size_bytes,
        modified_at=discovered_file.modified_at,
        title=discovered_file.title,
        artist=discovered_file.artist,
        album=discovered_file.album,
        duration_seconds=discovered_file.duration_seconds,
        bpm=discovered_file.bpm,
        key=discovered_file.key,
        comment=discovered_file.comment,
        raw_metadata=discovered_file.raw_metadata,
        status=AudioFileStatus.ACTIVE,
        first_seen_scan_id=scan_id,
        last_seen_scan_id=scan_id,
    )


def _seen_audio_file(
    existing: AudioFile,
    scan_id: str,
    discovered_file: DiscoveredAudioFile,
    *,
    refresh_metadata: bool,
) -> AudioFile:
    metadata = _metadata_values(existing, discovered_file, refresh=refresh_metadata)
    return AudioFile(
        id=existing.id,
        environment_id=existing.environment_id,
        path=discovered_file.path,
        size_bytes=discovered_file.size_bytes,
        modified_at=discovered_file.modified_at,
        title=metadata.title,
        artist=metadata.artist,
        album=metadata.album,
        duration_seconds=metadata.duration_seconds,
        bpm=metadata.bpm,
        key=metadata.key,
        comment=metadata.comment,
        raw_metadata=metadata.raw_metadata,
        status=AudioFileStatus.ACTIVE,
        first_seen_scan_id=existing.first_seen_scan_id or scan_id,
        last_seen_scan_id=scan_id,
    )


def _removed_audio_file(existing: AudioFile, removed_at: str) -> AudioFile:
    return AudioFile(
        id=existing.id,
        environment_id=existing.environment_id,
        path=existing.path,
        size_bytes=existing.size_bytes,
        modified_at=existing.modified_at,
        title=existing.title,
        artist=existing.artist,
        album=existing.album,
        duration_seconds=existing.duration_seconds,
        bpm=existing.bpm,
        key=existing.key,
        comment=existing.comment,
        raw_metadata=existing.raw_metadata,
        status=AudioFileStatus.REMOVED,
        first_seen_scan_id=existing.first_seen_scan_id,
        last_seen_scan_id=existing.last_seen_scan_id,
        removed_at=removed_at,
    )


def _same_file_state(existing: AudioFile, discovered_file: DiscoveredAudioFile) -> bool:
    return (
        existing.size_bytes == discovered_file.size_bytes
        and existing.modified_at == discovered_file.modified_at
    )


def _pop_moved_candidate(
    discovered_file: DiscoveredAudioFile,
    missing_active: list[AudioFile],
    moved_old_ids: set[str],
) -> AudioFile | None:
    for existing in missing_active:
        if existing.id in moved_old_ids:
            continue
        if (
            existing.path.name == discovered_file.path.name
            and existing.size_bytes == discovered_file.size_bytes
            and existing.modified_at == discovered_file.modified_at
        ):
            return existing
    return None


def _with_metadata(
    discovered_file: DiscoveredAudioFile,
    metadata: AudioMetadata,
) -> DiscoveredAudioFile:
    return DiscoveredAudioFile(
        path=discovered_file.path,
        size_bytes=discovered_file.size_bytes,
        modified_at=discovered_file.modified_at,
        title=metadata.title,
        artist=metadata.artist,
        album=metadata.album,
        duration_seconds=metadata.duration_seconds,
        bpm=metadata.bpm,
        key=metadata.key,
        comment=metadata.comment,
        raw_metadata=metadata.raw,
    )


@dataclass(frozen=True)
class _MetadataValues:
    title: str | None
    artist: str | None
    album: str | None
    duration_seconds: int | None
    bpm: int | None
    key: str | None
    comment: str | None
    raw_metadata: dict[str, object] | None


def _metadata_values(
    existing: AudioFile,
    discovered: DiscoveredAudioFile,
    *,
    refresh: bool,
) -> _MetadataValues:
    if refresh:
        return _MetadataValues(
            title=discovered.title,
            artist=discovered.artist,
            album=discovered.album,
            duration_seconds=discovered.duration_seconds,
            bpm=discovered.bpm,
            key=discovered.key,
            comment=discovered.comment,
            raw_metadata=discovered.raw_metadata,
        )
    return _MetadataValues(
        title=existing.title,
        artist=existing.artist,
        album=existing.album,
        duration_seconds=existing.duration_seconds,
        bpm=existing.bpm,
        key=existing.key,
        comment=existing.comment,
        raw_metadata=existing.raw_metadata,
    )
