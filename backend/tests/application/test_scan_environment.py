import sqlite3
from collections.abc import Callable
from pathlib import Path

from music_manager_backend.application.use_cases.scan_environment import ScanEnvironment
from music_manager_backend.domain.entities import MusicEnvironment
from music_manager_backend.domain.entities.audio_file import AudioFileStatus
from music_manager_backend.infrastructure.filesystem import LocalAudioScanner
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteScanRunRepository,
)


def test_scan_adds_and_then_marks_unchanged(
    sqlite_connection: sqlite3.Connection,
    music_environment_root: Path,
    create_audio_file: Callable[[str], Path],
) -> None:
    create_audio_file("track.mp3")
    _save_environment(sqlite_connection, music_environment_root)
    use_case = _scan_use_case(sqlite_connection)

    first = use_case.execute("env_1")
    second = use_case.execute("env_1")

    assert first.added == 1
    assert second.unchanged == 1
    assert second.total_active == 1


def test_rescan_marks_changed_and_removed_files(
    sqlite_connection: sqlite3.Connection,
    music_environment_root: Path,
    create_audio_file: Callable[[str], Path],
) -> None:
    changed = create_audio_file("changed.mp3")
    removed = create_audio_file("removed.mp3")
    _save_environment(sqlite_connection, music_environment_root)
    use_case = _scan_use_case(sqlite_connection)
    use_case.execute("env_1")

    changed.write_bytes(b"changed bytes")
    removed.unlink()
    summary = use_case.execute("env_1")

    assert summary.changed == 1
    assert summary.removed == 1
    removed_files = SqliteAudioFileRepository(sqlite_connection).list_by_environment(
        "env_1",
        status=AudioFileStatus.REMOVED,
    )
    assert len(removed_files) == 1


def test_rescan_detects_conservative_move(
    sqlite_connection: sqlite3.Connection,
    music_environment_root: Path,
    create_audio_file: Callable[[str], Path],
) -> None:
    original = create_audio_file("old/track.mp3")
    _save_environment(sqlite_connection, music_environment_root)
    use_case = _scan_use_case(sqlite_connection)
    use_case.execute("env_1")
    before = SqliteAudioFileRepository(sqlite_connection).list_by_environment("env_1")[0]

    moved = music_environment_root / "new" / "track.mp3"
    moved.parent.mkdir()
    original.rename(moved)
    summary = use_case.execute("env_1")
    after = SqliteAudioFileRepository(sqlite_connection).list_by_environment(
        "env_1",
        status=AudioFileStatus.ACTIVE,
    )[0]

    assert summary.moved == 1
    assert after.id == before.id
    assert after.path == moved


def _save_environment(sqlite_connection: sqlite3.Connection, root: Path) -> None:
    SqliteEnvironmentRepository(sqlite_connection).save(
        MusicEnvironment(id="env_1", name="Gig USB", root_path=root)
    )


def _scan_use_case(sqlite_connection: sqlite3.Connection) -> ScanEnvironment:
    return ScanEnvironment(
        environments=SqliteEnvironmentRepository(sqlite_connection),
        audio_files=SqliteAudioFileRepository(sqlite_connection),
        scan_runs=SqliteScanRunRepository(sqlite_connection),
        scanner_factory=LocalAudioScanner,
    )
