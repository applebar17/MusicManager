from collections.abc import Callable
from pathlib import Path

from music_manager_backend.domain.entities import (
    AudioFile,
    DiscoveredAudioFile,
    ScanRun,
    ScanSummary,
)
from music_manager_backend.domain.entities.audio_file import AudioFileStatus
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
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files
        self.scan_runs = scan_runs
        self.scanner_factory = scanner_factory

    def execute(self, environment_id: str) -> ScanSummary:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        scan_id = new_id("scan")
        started_at = utc_now_iso()
        scanner = self.scanner_factory(environment.root_path)
        discovered = scanner.scan()
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
                    self.audio_files.save(_seen_audio_file(moved, scan_id, discovered_file))
                    moved_old_ids.add(moved.id)
                    moved_new_paths.add(discovered_file.path)
                    counts.moved += 1
                continue

            self.audio_files.save(_seen_audio_file(existing, scan_id, discovered_file))
            if _same_file_state(existing, discovered_file):
                counts.unchanged += 1
            else:
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
        duration_seconds=discovered_file.duration_seconds,
        status=AudioFileStatus.ACTIVE,
        first_seen_scan_id=scan_id,
        last_seen_scan_id=scan_id,
    )


def _seen_audio_file(
    existing: AudioFile,
    scan_id: str,
    discovered_file: DiscoveredAudioFile,
) -> AudioFile:
    return AudioFile(
        id=existing.id,
        environment_id=existing.environment_id,
        path=discovered_file.path,
        size_bytes=discovered_file.size_bytes,
        modified_at=discovered_file.modified_at,
        title=existing.title or discovered_file.title,
        artist=existing.artist or discovered_file.artist,
        duration_seconds=existing.duration_seconds or discovered_file.duration_seconds,
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
        duration_seconds=existing.duration_seconds,
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
