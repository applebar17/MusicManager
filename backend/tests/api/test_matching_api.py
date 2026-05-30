from pathlib import Path
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from music_manager_backend.api.container import AppContainer
from music_manager_backend.domain.entities import (
    AudioFile,
    MatchLink,
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
    assert review[0]["match"]["source_area"] == "usb"
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


def test_manual_file_candidates_include_unmapped_usb_and_download_files(
    api_client: TestClient,
) -> None:
    container = _container(api_client)
    _seed_matching_data(container, download_path=Path("/Users/test/Downloads"))
    with container.repository_bundle() as repositories:
        repositories.audio_file_repository.save(
            AudioFile(
                id="download_file",
                environment_id="env_1",
                path=Path("/Users/test/Downloads/Samuele Mogavero - Cross The Tracks.mp3"),
                size_bytes=1,
                modified_at=1.0,
                duration_seconds=301,
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="usb_file",
                environment_id="env_1",
                path=Path("/Volumes/USB/Samuele Mogavero - Cross The Tracks.mp3"),
                size_bytes=1,
                modified_at=1.0,
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="linked_file",
                environment_id="env_1",
                path=Path("/Volumes/USB/linked-track.mp3"),
                size_bytes=1,
                modified_at=1.0,
                title="Track One",
                artist="Artist",
            )
        )
        repositories.match_link_repository.save(
            MatchLink(
                song_id="song_1",
                audio_file_id="linked_file",
                method="manual",
                confidence=1.0,
                reviewed=True,
            )
        )

    response = api_client.get(
        "/environments/env_1/matching/manual-file-candidates",
        params={"song_id": "song_2", "q": "cross tracks"},
    )

    assert response.status_code == 200
    rows = {row["audio_file_id"]: row for row in response.json()}
    assert rows["download_file"]["source_area"] == "download"
    assert rows["download_file"]["method"] == "manual_search"
    assert rows["download_file"]["confidence"] == 0.0
    assert rows["usb_file"]["source_area"] == "usb"
    assert "linked_file" not in rows


def test_match_downloads_requires_download_path(api_client: TestClient) -> None:
    container = _container(api_client)
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )

    response = api_client.post("/environments/env_1/matching/downloads/run")

    assert response.status_code == 400
    assert response.json()["code"] == "download_path_required"


def _container(api_client: TestClient) -> AppContainer:
    app = cast(FastAPI, api_client.app)
    return cast(AppContainer, app.state.container)


def _seed_matching_data(container: AppContainer, download_path: Path | None = None) -> None:
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(
                id="env_1",
                name="USB",
                root_path=Path("/Volumes/USB"),
                download_path=download_path,
            )
        )
        repositories.song_repository.save(
            SongMaster(id="song_1", title="Track One", artist="Artist")
        )
        repositories.song_repository.save(
            SongMaster(id="song_2", title="Track Two", artist="Artist")
        )
        repositories.playlist_repository.save(
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
        repositories.audio_file_repository.save(
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
        repositories.audio_file_repository.save(
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
        repositories.audio_file_repository.save(
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
