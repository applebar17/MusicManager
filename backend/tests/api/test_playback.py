from pathlib import Path
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from music_manager_backend.api.container import AppContainer
from music_manager_backend.domain.entities import AudioFile, AudioFileStatus


def test_playback_streams_active_audio_file(api_client: TestClient, tmp_path: Path) -> None:
    environment_id, audio_file_id = _create_environment_and_audio_file(
        api_client,
        tmp_path,
        content=b"0123456789",
    )

    response = api_client.get(
        f"/environments/{environment_id}/playback/audio-files/{audio_file_id}"
    )

    assert response.status_code == 200
    assert response.content == b"0123456789"
    assert response.headers["content-type"] in {"audio/mpeg", "audio/mpeg3"}


def test_playback_supports_basic_range_requests(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    environment_id, audio_file_id = _create_environment_and_audio_file(
        api_client,
        tmp_path,
        content=b"0123456789",
    )

    response = api_client.get(
        f"/environments/{environment_id}/playback/audio-files/{audio_file_id}",
        headers={"Range": "bytes=2-5"},
    )

    assert response.status_code in {200, 206}
    if response.status_code == 206:
        assert response.content == b"2345"
        assert response.headers["content-range"].startswith("bytes 2-5/")


def test_playback_missing_environment_returns_404(api_client: TestClient) -> None:
    response = api_client.get("/environments/env_missing/playback/audio-files/file_1")

    assert response.status_code == 404


def test_playback_removed_audio_file_returns_400(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    environment_id, audio_file_id = _create_environment_and_audio_file(
        api_client,
        tmp_path,
        status=AudioFileStatus.REMOVED,
    )

    response = api_client.get(
        f"/environments/{environment_id}/playback/audio-files/{audio_file_id}"
    )

    assert response.status_code == 400


def test_playback_missing_file_on_disk_returns_404(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    environment_id, audio_file_id = _create_environment_and_audio_file(api_client, tmp_path)
    container = _container(api_client)
    with container.repository_bundle() as repositories:
        audio_file = repositories.audio_file_repository.get(audio_file_id)
    assert audio_file is not None
    audio_file.path.unlink()

    response = api_client.get(
        f"/environments/{environment_id}/playback/audio-files/{audio_file_id}"
    )

    assert response.status_code == 404


def test_matching_candidate_audio_file_can_be_streamed(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    environment_id, audio_file_id = _create_environment_and_audio_file(
        api_client,
        tmp_path,
        content=b"candidate",
    )

    response = api_client.get(
        f"/environments/{environment_id}/playback/audio-files/{audio_file_id}"
    )

    assert response.status_code == 200
    assert response.content == b"candidate"


def test_download_audio_file_can_be_streamed(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    root = tmp_path / "usb"
    downloads = tmp_path / "downloads"
    root.mkdir()
    downloads.mkdir()
    track = downloads / "track.mp3"
    track.write_bytes(b"download")
    environment_id = api_client.post(
        "/environments",
        json={
            "name": "USB",
            "root_path": str(root),
            "download_path": str(downloads),
        },
    ).json()["id"]
    with _container(api_client).repository_bundle() as repositories:
        repositories.audio_file_repository.save(
            AudioFile(
                id="download_file",
                environment_id=environment_id,
                path=track,
                size_bytes=8,
                modified_at=1.0,
            )
        )

    response = api_client.get(
        f"/environments/{environment_id}/playback/audio-files/download_file"
    )

    assert response.status_code == 200
    assert response.content == b"download"


def _create_environment_and_audio_file(
    api_client: TestClient,
    tmp_path: Path,
    *,
    content: bytes = b"audio",
    status: AudioFileStatus = AudioFileStatus.ACTIVE,
) -> tuple[str, str]:
    root = tmp_path / "usb"
    root.mkdir()
    track = root / "track.mp3"
    track.write_bytes(content)
    environment_id = api_client.post(
        "/environments",
        json={"name": "USB", "root_path": str(root)},
    ).json()["id"]
    audio_file_id = "file_1"
    with _container(api_client).repository_bundle() as repositories:
        repositories.audio_file_repository.save(
            AudioFile(
                id=audio_file_id,
                environment_id=environment_id,
                path=track,
                size_bytes=len(content),
                modified_at=1.0,
                status=status,
            )
        )
    return environment_id, audio_file_id


def _container(api_client: TestClient) -> AppContainer:
    app = cast(FastAPI, api_client.app)
    return cast(AppContainer, app.state.container)
