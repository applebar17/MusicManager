import sqlite3
from collections.abc import Callable
from pathlib import Path

from music_manager_backend.application.use_cases.scan_environment import ScanEnvironment
from music_manager_backend.domain.entities import AudioMetadata, MusicEnvironment
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


def test_full_scan_includes_download_folder(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    root = tmp_path / "usb"
    downloads = tmp_path / "downloads"
    root.mkdir()
    downloads.mkdir()
    (root / "usb-track.mp3").write_bytes(b"usb")
    (downloads / "download-track.mp3").write_bytes(b"download")
    _save_environment(sqlite_connection, root, download_path=downloads)

    summary = _scan_use_case(sqlite_connection).execute("env_1")

    assert summary.added == 2
    paths = {
        item.path
        for item in SqliteAudioFileRepository(sqlite_connection).list_by_environment("env_1")
    }
    assert paths == {root / "usb-track.mp3", downloads / "download-track.mp3"}


def test_scoped_download_scan_does_not_mark_usb_files_removed(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    root = tmp_path / "usb"
    downloads = tmp_path / "downloads"
    root.mkdir()
    downloads.mkdir()
    usb_track = root / "usb-track.mp3"
    download_track = downloads / "download-track.mp3"
    usb_track.write_bytes(b"usb")
    download_track.write_bytes(b"download")
    _save_environment(sqlite_connection, root, download_path=downloads)
    use_case = _scan_use_case(sqlite_connection)
    use_case.execute("env_1")

    download_track.unlink()
    summary = use_case.execute_roots("env_1", [downloads])

    assert summary.removed == 1
    active_paths = {
        item.path
        for item in SqliteAudioFileRepository(sqlite_connection).list_by_environment(
            "env_1",
            status=AudioFileStatus.ACTIVE,
        )
    }
    removed_paths = {
        item.path
        for item in SqliteAudioFileRepository(sqlite_connection).list_by_environment(
            "env_1",
            status=AudioFileStatus.REMOVED,
        )
    }
    assert active_paths == {usb_track}
    assert removed_paths == {download_track}


def _save_environment(
    sqlite_connection: sqlite3.Connection,
    root: Path,
    *,
    download_path: Path | None = None,
) -> None:
    SqliteEnvironmentRepository(sqlite_connection).save(
        MusicEnvironment(id="env_1", name="Gig USB", root_path=root, download_path=download_path)
    )


def _scan_use_case(sqlite_connection: sqlite3.Connection) -> ScanEnvironment:
    return ScanEnvironment(
        environments=SqliteEnvironmentRepository(sqlite_connection),
        audio_files=SqliteAudioFileRepository(sqlite_connection),
        scan_runs=SqliteScanRunRepository(sqlite_connection),
        scanner_factory=LocalAudioScanner,
        metadata_reader=FakeMetadataReader(),
    )


def test_scan_persists_and_refreshes_metadata(
    sqlite_connection: sqlite3.Connection,
    music_environment_root: Path,
    create_audio_file: Callable[[str], Path],
) -> None:
    track = create_audio_file("track.mp3")
    _save_environment(sqlite_connection, music_environment_root)
    reader = FakeMetadataReader()
    reader.metadata_by_path[track] = AudioMetadata(
        title="First Title",
        artist="Artist",
        album="Album",
        duration_seconds=200,
        bpm=124,
        key="8A",
        comment="Warmup",
        raw={"title": "First Title"},
    )
    use_case = ScanEnvironment(
        environments=SqliteEnvironmentRepository(sqlite_connection),
        audio_files=SqliteAudioFileRepository(sqlite_connection),
        scan_runs=SqliteScanRunRepository(sqlite_connection),
        scanner_factory=LocalAudioScanner,
        metadata_reader=reader,
    )

    use_case.execute("env_1")
    persisted = SqliteAudioFileRepository(sqlite_connection).list_by_environment("env_1")[0]
    assert persisted.title == "First Title"
    assert persisted.bpm == 124
    assert persisted.raw_metadata == {"title": "First Title"}

    reader.metadata_by_path[track] = AudioMetadata(title="Ignored Title")
    unchanged = use_case.execute("env_1")
    persisted = SqliteAudioFileRepository(sqlite_connection).list_by_environment("env_1")[0]
    assert unchanged.unchanged == 1
    assert persisted.title == "First Title"

    track.write_bytes(b"changed bytes")
    reader.metadata_by_path[track] = AudioMetadata(title="Second Title")
    changed = use_case.execute("env_1")
    persisted = SqliteAudioFileRepository(sqlite_connection).list_by_environment("env_1")[0]
    assert changed.changed == 1
    assert persisted.title == "Second Title"


class FakeMetadataReader:
    def __init__(self) -> None:
        self.metadata_by_path: dict[Path, AudioMetadata] = {}

    def read(self, path: Path) -> AudioMetadata:
        return self.metadata_by_path.get(path, AudioMetadata())
