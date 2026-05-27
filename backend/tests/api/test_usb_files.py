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


def test_usb_files_lists_matches_warnings_and_folder_parts(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    root = _seed_usb_data(_container(api_client), tmp_path)

    response = api_client.get("/environments/env_1/usb/files")

    assert response.status_code == 200
    rows = {row["audio_file_id"]: row for row in response.json()}
    assert rows["file_matched"]["relative_path"] == "01_TECH/Track One.mp3"
    assert rows["file_matched"]["folder_parts"] == ["01_TECH"]
    assert rows["file_matched"]["match_status"] == "matched"
    assert rows["file_matched"]["matched_song"]["song_id"] == "song_1"
    assert rows["file_matched"]["matched_song"]["playlists"] == ["USB Set"]
    assert rows["file_preview"]["match_status"] == "unmatched"
    assert rows["file_preview"]["warnings"] == ["likely_preview_download"]
    assert (root / "01_TECH" / "Track One.mp3").exists()


def test_usb_candidate_search_scores_missing_imported_songs(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    _seed_usb_data(_container(api_client), tmp_path)

    response = api_client.get(
        "/environments/env_1/usb/match-candidates",
        params={"audio_file_id": "file_candidate", "q": "missing"},
    )

    assert response.status_code == 200
    assert response.json()[0] == {
        "song_id": "song_2",
        "title": "Missing Song",
        "artist": "Artist",
        "duration_seconds": 180,
        "playlists": ["USB Set"],
        "status": "ambiguous",
        "method": "metadata_exact",
        "confidence": 0.95,
    }


def test_usb_candidate_search_includes_already_matched_songs(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    _seed_usb_data(_container(api_client), tmp_path)

    response = api_client.get(
        "/environments/env_1/usb/match-candidates",
        params={"audio_file_id": "file_duplicate", "q": "track one"},
    )

    assert response.status_code == 200
    assert response.json()[0]["song_id"] == "song_1"
    assert response.json()[0]["status"] == "manually_mapped"
    assert response.json()[0]["method"] == "metadata_exact"


def test_usb_manual_mapping_updates_usb_row(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    _seed_usb_data(_container(api_client), tmp_path)

    mapping = api_client.post(
        "/environments/env_1/matching/manual-mappings",
        json={"song_id": "song_2", "audio_file_id": "file_candidate"},
    )
    files = api_client.get("/environments/env_1/usb/files")

    assert mapping.status_code == 200
    rows = {row["audio_file_id"]: row for row in files.json()}
    assert rows["file_candidate"]["match_status"] == "matched"
    assert rows["file_candidate"]["matched_song"]["song_id"] == "song_2"
    assert rows["file_candidate"]["matched_song"]["reviewed"] is True


def test_usb_mapping_adds_link_without_removing_existing_copy(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    _seed_usb_data(container, tmp_path)

    response = api_client.post(
        "/environments/env_1/usb/audio-files/file_duplicate/mapping",
        json={"song_id": "song_1"},
    )
    files = api_client.get("/environments/env_1/usb/files")

    assert response.status_code == 200
    rows = {row["audio_file_id"]: row for row in files.json()}
    assert rows["file_matched"]["match_status"] == "matched"
    assert rows["file_duplicate"]["match_status"] == "matched"
    assert rows["file_matched"]["matched_song"]["local_copy_count"] == 2
    assert rows["file_duplicate"]["matched_song"]["local_copy_count"] == 2
    with container.repository_bundle() as repositories:
        linked_audio_file_ids = {
            link.audio_file_id
            for link in repositories.match_link_repository.list_by_song("song_1")
        }
        assert linked_audio_file_ids == {
            "file_matched",
            "file_duplicate",
        }


def test_usb_quarantine_moves_file_and_removes_matches(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = _seed_usb_data(container, tmp_path)

    response = api_client.post("/environments/env_1/usb/audio-files/file_matched/quarantine")

    assert response.status_code == 200
    data = response.json()
    assert data["audio_status"] == "removed"
    assert data["match_status"] == "unmatched"
    assert not (root / "01_TECH" / "Track One.mp3").exists()
    assert (root / ".music_manager" / "_deprecated" / "Track One.mp3").read_bytes() == b"audio"
    with container.repository_bundle() as repositories:
        removed_audio_file = repositories.audio_file_repository.get("file_matched")
        assert removed_audio_file is not None
        assert removed_audio_file.status.value == "removed"
        assert repositories.match_link_repository.list_by_song("song_1") == []


def test_usb_batch_quarantine_requires_delete_confirmation(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    _seed_usb_data(_container(api_client), tmp_path)

    response = api_client.post(
        "/environments/env_1/usb/audio-files/quarantine",
        json={"audio_file_ids": ["file_matched"], "confirmation": "remove"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "delete_confirmation_required"


def test_usb_batch_quarantine_moves_selected_files(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = _seed_usb_data(container, tmp_path)

    response = api_client.post(
        "/environments/env_1/usb/audio-files/quarantine",
        json={
            "audio_file_ids": ["file_matched", "file_candidate"],
            "confirmation": "delete",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["removed"] == 2
    assert {item["audio_file_id"] for item in data["files"]} == {
        "file_matched",
        "file_candidate",
    }
    assert not (root / "01_TECH" / "Track One.mp3").exists()
    assert not (root / "03_HOUSE" / "Missing Song.mp3").exists()
    assert (root / ".music_manager" / "_deprecated" / "Track One.mp3").read_bytes() == b"audio"
    assert (
        root / ".music_manager" / "_deprecated" / "Missing Song.mp3"
    ).read_bytes() == b"candidate"
    with container.repository_bundle() as repositories:
        matched = repositories.audio_file_repository.get("file_matched")
        candidate = repositories.audio_file_repository.get("file_candidate")
        assert matched is not None
        assert candidate is not None
        assert matched.status.value == "removed"
        assert candidate.status.value == "removed"
        assert repositories.match_link_repository.list_by_song("song_1") == []


def test_usb_quarantine_rejects_outside_root_paths(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = _seed_usb_data(container, tmp_path)
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"outside")
    with container.repository_bundle() as repositories:
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_outside",
                environment_id="env_1",
                path=outside,
                size_bytes=7,
                modified_at=4.0,
            )
        )

    response = api_client.post("/environments/env_1/usb/audio-files/file_outside/quarantine")

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert outside.exists()
    assert root.exists()


def test_usb_quarantine_one_duplicate_keeps_sibling_matched(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = _seed_usb_data(container, tmp_path)
    api_client.post(
        "/environments/env_1/usb/audio-files/file_duplicate/mapping",
        json={"song_id": "song_1"},
    )

    response = api_client.post("/environments/env_1/usb/audio-files/file_duplicate/quarantine")
    files = api_client.get("/environments/env_1/usb/files")

    assert response.status_code == 200
    rows = {row["audio_file_id"]: row for row in files.json()}
    assert rows["file_matched"]["match_status"] == "matched"
    assert rows["file_matched"]["matched_song"]["local_copy_count"] == 1
    assert not (root / "04_DANCE" / "Track One.mp3").exists()


def _container(api_client: TestClient) -> AppContainer:
    app = cast(FastAPI, api_client.app)
    return cast(AppContainer, app.state.container)


def _seed_usb_data(container: AppContainer, tmp_path: Path) -> Path:
    root = tmp_path / "TORDIS"
    (root / "01_TECH").mkdir(parents=True)
    (root / "03_HOUSE").mkdir()
    (root / "04_DANCE").mkdir()
    (root / "08_POP").mkdir()
    matched_path = root / "01_TECH" / "Track One.mp3"
    duplicate_path = root / "04_DANCE" / "Track One.mp3"
    preview_path = root / "08_POP" / "Preview.mp3"
    candidate_path = root / "03_HOUSE" / "Missing Song.mp3"
    matched_path.write_bytes(b"audio")
    duplicate_path.write_bytes(b"duplicate")
    preview_path.write_bytes(b"preview")
    candidate_path.write_bytes(b"candidate")
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="TORDIS", root_path=root)
        )
        repositories.song_repository.save(
            SongMaster(id="song_1", title="Track One", artist="Artist", duration_seconds=210)
        )
        repositories.song_repository.save(
            SongMaster(id="song_2", title="Missing Song", artist="Artist", duration_seconds=180)
        )
        repositories.playlist_repository.save(
            Playlist(
                id="playlist_1",
                environment_id="env_1",
                name="USB Set",
                items=(
                    PlaylistItem(song_id="song_1", position=1),
                    PlaylistItem(song_id="song_2", position=2),
                ),
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_matched",
                environment_id="env_1",
                path=matched_path,
                size_bytes=5,
                modified_at=1.0,
                title="Track One",
                artist="Artist",
                duration_seconds=210,
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_preview",
                environment_id="env_1",
                path=preview_path,
                size_bytes=7,
                modified_at=2.0,
                title="Preview",
                artist="Artist",
                duration_seconds=32,
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_duplicate",
                environment_id="env_1",
                path=duplicate_path,
                size_bytes=9,
                modified_at=2.5,
                title="Track One",
                artist="Artist",
                duration_seconds=212,
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_candidate",
                environment_id="env_1",
                path=candidate_path,
                size_bytes=9,
                modified_at=3.0,
                title="Missing Song",
                artist="Artist",
                duration_seconds=180,
            )
        )
        repositories.match_link_repository.save(
            MatchLink(
                song_id="song_1",
                audio_file_id="file_matched",
                method="manual",
                confidence=1.0,
                reviewed=True,
            )
        )
    return root
