from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from music_manager_backend.api.app import create_app


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(create_app())


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
