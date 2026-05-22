import sqlite3
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from music_manager_backend.api.app import create_app
from music_manager_backend.infrastructure.persistence.migration_runner import upgrade_database
from music_manager_backend.infrastructure.persistence.sqlite import connect
from music_manager_backend.shared.settings import Settings


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "music-manager-test.sqlite3"


@pytest.fixture
def migrated_database_path(database_path: Path) -> Path:
    upgrade_database(database_path)
    return database_path


@pytest.fixture
def sqlite_connection(migrated_database_path: Path) -> Generator[sqlite3.Connection, None, None]:
    connection = connect(migrated_database_path)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def api_settings(migrated_database_path: Path) -> Settings:
    return Settings(environment="test", database_path=migrated_database_path)


@pytest.fixture
def api_client(api_settings: Settings) -> TestClient:
    return TestClient(create_app(api_settings))


@pytest.fixture
def music_environment_root(tmp_path: Path) -> Path:
    root = tmp_path / "music-environment"
    root.mkdir()
    return root


@pytest.fixture
def create_audio_file(music_environment_root: Path) -> Callable[[str], Path]:
    def _create_audio_file(relative_path: str) -> Path:
        path = music_environment_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake audio fixture")
        return path

    return _create_audio_file


@pytest.fixture
def create_unsupported_file(music_environment_root: Path) -> Callable[[str], Path]:
    def _create_unsupported_file(relative_path: str) -> Path:
        path = music_environment_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not an audio file", encoding="utf-8")
        return path

    return _create_unsupported_file
