from pathlib import Path
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from music_manager_backend.api.container import AppContainer
from music_manager_backend.domain.entities import (
    AudioFile,
    MusicEnvironment,
    Playlist,
    PlaylistItem,
    SongMaster,
)


def test_matching_run_review_and_manual_mapping_api(
    api_client: TestClient,
) -> None:
    container = _container(api_client)
    _seed_matching_data(container)

    run_response = api_client.post("/environments/env_1/matching/run")
    review_response = api_client.get("/environments/env_1/matching/review")
    manual_response = api_client.post(
        "/environments/env_1/matching/manual-mappings",
        json={"song_id": "song_2", "audio_file_id": "file_2"},
    )

    assert run_response.status_code == 200
    assert run_response.json()["matched"] == 1
    assert run_response.json()["ambiguous"] == 1
    assert review_response.status_code == 200
    review = sorted(review_response.json(), key=lambda row: row["song_id"])
    assert review[0]["status"] == "matched"
    assert review[0]["match"]["audio_file_id"] == "file_1"
    assert review[1]["status"] == "ambiguous"
    assert len(review[1]["candidates"]) == 2
    assert manual_response.status_code == 200
    assert manual_response.json()["status"] == "manually_mapped"
    assert manual_response.json()["match"]["audio_file_id"] == "file_2"


def test_matching_missing_environment_returns_404(api_client: TestClient) -> None:
    response = api_client.post("/environments/env_missing/matching/run")

    assert response.status_code == 404


def test_manual_mapping_invalid_audio_file_returns_400(api_client: TestClient) -> None:
    container = _container(api_client)
    _seed_matching_data(container)

    response = api_client.post(
        "/environments/env_1/matching/manual-mappings",
        json={"song_id": "song_1", "audio_file_id": "missing_file"},
    )

    assert response.status_code == 400


def _container(api_client: TestClient) -> AppContainer:
    app = cast(FastAPI, api_client.app)
    return cast(AppContainer, app.state.container)


def _seed_matching_data(container: AppContainer) -> None:
    container.environment_repository.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    container.song_repository.save(SongMaster(id="song_1", title="Track One", artist="Artist"))
    container.song_repository.save(SongMaster(id="song_2", title="Track Two", artist="Artist"))
    container.playlist_repository.save(
        Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(
                PlaylistItem(song_id="song_1", position=1),
                PlaylistItem(song_id="song_2", position=2),
            ),
        )
    )
    container.audio_file_repository.save(
        AudioFile(
            id="file_1",
            environment_id="env_1",
            path=Path("/Volumes/USB/track-one.mp3"),
            size_bytes=1,
            modified_at=1.0,
            title="Track One",
            artist="Artist",
        )
    )
    container.audio_file_repository.save(
        AudioFile(
            id="file_2",
            environment_id="env_1",
            path=Path("/Volumes/USB/track-two-a.mp3"),
            size_bytes=1,
            modified_at=1.0,
            title="Track Two",
            artist="Artist",
        )
    )
    container.audio_file_repository.save(
        AudioFile(
            id="file_3",
            environment_id="env_1",
            path=Path("/Volumes/USB/track-two-b.mp3"),
            size_bytes=1,
            modified_at=1.0,
            title="Track Two",
            artist="Artist",
        )
    )
