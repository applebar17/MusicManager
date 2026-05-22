import os
import sqlite3
from pathlib import Path

import pytest

from music_manager_backend.application.use_cases.get_playback_file import GetPlaybackFile
from music_manager_backend.domain.entities import AudioFile, AudioFileStatus, MusicEnvironment
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError


def test_get_playback_file_resolves_active_file_inside_environment(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = tmp_path / "usb"
    root.mkdir()
    track = root / "track.mp3"
    track.write_bytes(b"audio")
    _save_environment(repositories, root)
    repositories.audio_files.save(_audio_file(path=track))

    playback_file = _use_case(repositories).execute("env_1", "file_1")

    assert playback_file.path == track.resolve()
    assert playback_file.filename == "track.mp3"


def test_get_playback_file_rejects_missing_environment(
    sqlite_connection: sqlite3.Connection,
) -> None:
    with pytest.raises(NotFoundError):
        _use_case(_repositories(sqlite_connection)).execute("env_missing", "file_1")


def test_get_playback_file_rejects_missing_audio_file(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = tmp_path / "usb"
    root.mkdir()
    _save_environment(repositories, root)

    with pytest.raises(NotFoundError):
        _use_case(repositories).execute("env_1", "file_missing")


def test_get_playback_file_rejects_removed_audio_file(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = tmp_path / "usb"
    root.mkdir()
    track = root / "track.mp3"
    track.write_bytes(b"audio")
    _save_environment(repositories, root)
    repositories.audio_files.save(_audio_file(path=track, status=AudioFileStatus.REMOVED))

    with pytest.raises(ValidationError):
        _use_case(repositories).execute("env_1", "file_1")


def test_get_playback_file_rejects_missing_file_on_disk(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = tmp_path / "usb"
    root.mkdir()
    _save_environment(repositories, root)
    repositories.audio_files.save(_audio_file(path=root / "missing.mp3"))

    with pytest.raises(NotFoundError):
        _use_case(repositories).execute("env_1", "file_1")


def test_get_playback_file_rejects_directory_paths(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = tmp_path / "usb"
    root.mkdir()
    directory = root / "folder"
    directory.mkdir()
    _save_environment(repositories, root)
    repositories.audio_files.save(_audio_file(path=directory))

    with pytest.raises(ValidationError):
        _use_case(repositories).execute("env_1", "file_1")


def test_get_playback_file_rejects_paths_outside_environment_root(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = tmp_path / "usb"
    root.mkdir()
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"audio")
    _save_environment(repositories, root)
    repositories.audio_files.save(_audio_file(path=outside))

    with pytest.raises(ValidationError):
        _use_case(repositories).execute("env_1", "file_1")


def test_get_playback_file_rejects_symlink_outside_environment_root(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = tmp_path / "usb"
    root.mkdir()
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"audio")
    symlink = root / "link.mp3"
    symlink.symlink_to(outside)
    _save_environment(repositories, root)
    repositories.audio_files.save(_audio_file(path=symlink))

    with pytest.raises(ValidationError):
        _use_case(repositories).execute("env_1", "file_1")


def test_get_playback_file_rejects_unreadable_files(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = tmp_path / "usb"
    root.mkdir()
    track = root / "track.mp3"
    track.write_bytes(b"audio")
    _save_environment(repositories, root)
    repositories.audio_files.save(_audio_file(path=track))
    original_mode = track.stat().st_mode
    track.chmod(0)
    try:
        if os.access(track, os.R_OK):
            pytest.skip("Current user can still read chmod 0 files")
        with pytest.raises(ValidationError):
            _use_case(repositories).execute("env_1", "file_1")
    finally:
        track.chmod(original_mode)


class _Repositories:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.environments = SqliteEnvironmentRepository(connection)
        self.audio_files = SqliteAudioFileRepository(connection)


def _repositories(connection: sqlite3.Connection) -> _Repositories:
    return _Repositories(connection)


def _save_environment(repositories: _Repositories, root: Path) -> None:
    repositories.environments.save(MusicEnvironment(id="env_1", name="USB", root_path=root))


def _audio_file(
    *,
    path: Path,
    status: AudioFileStatus = AudioFileStatus.ACTIVE,
) -> AudioFile:
    return AudioFile(
        id="file_1",
        environment_id="env_1",
        path=path,
        size_bytes=1,
        modified_at=1.0,
        status=status,
    )


def _use_case(repositories: _Repositories) -> GetPlaybackFile:
    return GetPlaybackFile(
        environments=repositories.environments,
        audio_files=repositories.audio_files,
    )
