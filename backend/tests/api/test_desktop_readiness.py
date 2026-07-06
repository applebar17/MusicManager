from dataclasses import replace
from pathlib import Path
from time import sleep
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from music_manager_backend.api.container import AppContainer
from music_manager_backend.domain.entities import (
    AudioFile,
    AudioFileStatus,
    ExportApplyItemResult,
    ExportApplyItemStatus,
    ExportApplyRun,
    ExportApplyRunStatus,
    ExportPlan,
    LibraryTrack,
    LibraryTrackStatus,
    MatchLink,
    MusicEnvironment,
    MusicLibrary,
    Playlist,
    PlaylistItem,
    SongLibraryLink,
    SongMaster,
)
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.ports.soundcloud_models import (
    ParsedSoundCloudPlaylist,
    ParsedSoundCloudTrack,
)
from music_manager_backend.shared.settings import Settings

SOURCE_URL = "https://soundcloud.com/user/sets/funk"


class FakeSoundCloudImporter:
    def __init__(self, playlist: ParsedSoundCloudPlaylist) -> None:
        self.playlist = playlist

    def import_playlist(self, url: str) -> ParsedSoundCloudPlaylist:
        return self.playlist


def test_environment_overview_and_playlist_views(api_client: TestClient) -> None:
    container = _container(api_client)
    _seed_desktop_view_data(container)

    overview_response = api_client.get("/environments/env_1/overview")
    playlists_response = api_client.get("/environments/env_1/playlists")
    detail_response = api_client.get("/environments/env_1/playlists/playlist_1")

    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["playlist_count"] == 1
    assert overview["active_playlist_item_count"] == 3
    assert overview["inactive_playlist_item_count"] == 1
    assert overview["unique_song_count"] == 3
    assert overview["active_audio_file_count"] == 2
    assert overview["removed_audio_file_count"] == 1
    assert overview["unmanaged_audio_file_count"] == 1
    assert overview["matched_count"] == 1
    assert overview["missing_audio_count"] == 1
    assert overview["ambiguous_count"] == 1

    assert playlists_response.status_code == 200
    playlist = playlists_response.json()[0]
    assert playlist["name"] == "Set"
    assert playlist["active_item_count"] == 3
    assert playlist["inactive_item_count"] == 1
    assert playlist["matched_count"] == 1
    assert playlist["missing_audio_count"] == 1
    assert playlist["ambiguous_count"] == 1

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert [item["song_id"] for item in detail["items"]] == [
        "song_1",
        "song_2",
        "song_3",
    ]
    assert [item["song_id"] for item in detail["removed_items"]] == ["song_4"]
    assert detail["items"][0]["match_status"] == "matched"
    assert detail["items"][0]["accepted_library_track_id"] == "library_matched"
    assert detail["items"][0]["accepted_library_filename"] == "matched.mp3"
    assert detail["items"][0]["accepted_audio_file_id"] is None
    assert detail["items"][0]["playback_url"] is None
    assert detail["items"][1]["match_status"] == "ambiguous"
    assert detail["removed_items"][0]["remote_membership_active"] is False


def test_playlist_detail_rejects_wrong_environment(api_client: TestClient) -> None:
    container = _container(api_client)
    _seed_desktop_view_data(container)
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_2", name="Other", root_path=Path("/Volumes/OTHER"))
        )

    response = api_client.get("/environments/env_2/playlists/playlist_1")

    assert response.status_code == 404


def test_playlist_local_items_can_be_added_and_removed(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    library_root = tmp_path / "library"
    root.mkdir()
    library_root.mkdir()
    local_file = root / "Loose Track.mp3"
    local_file.write_bytes(b"fake audio")
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=root)
        )
        repositories.library_repository.save_default(
            MusicLibrary(
                id="default",
                root_path=library_root,
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
        repositories.playlist_repository.save(
            Playlist(id="playlist_1", environment_id="env_1", name="Set")
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_local",
                environment_id="env_1",
                path=local_file,
                size_bytes=12,
                modified_at=1.0,
                title="Loose Track",
                artist="Local Artist",
                duration_seconds=180,
            )
        )

    added = api_client.post(
        "/environments/env_1/playlists/playlist_1/local-items",
        json={"audio_file_id": "file_local"},
    )

    assert added.status_code == 200
    body = added.json()
    assert body["active_item_count"] == 1
    assert body["inactive_item_count"] == 0
    assert body["items"][0]["title"] == "Loose Track"
    assert body["items"][0]["local_membership_active"] is True
    assert body["items"][0]["remote_membership_active"] is False
    assert body["items"][0]["added_by_local_audio_file_id"] == "file_local"
    assert body["items"][0]["match_status"] == "manually_mapped"
    assert body["items"][0]["library_match_status"] == "manually_mapped_library"
    assert body["items"][0]["accepted_library_filename"] == "Loose Track.mp3"

    song_id = body["items"][0]["song_id"]
    removed = api_client.delete(
        f"/environments/env_1/playlists/playlist_1/local-items/{song_id}"
    )

    assert removed.status_code == 200
    assert removed.json()["items"] == []
    assert removed.json()["removed_items"] == []


def test_playlist_local_item_rejects_inactive_audio_file(api_client: TestClient) -> None:
    container = _container(api_client)
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )
        repositories.playlist_repository.save(
            Playlist(id="playlist_1", environment_id="env_1", name="Set")
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_removed",
                environment_id="env_1",
                path=Path("/Volumes/USB/Removed.mp3"),
                size_bytes=12,
                modified_at=1.0,
                status=AudioFileStatus.REMOVED,
            )
        )

    response = api_client.post(
        "/environments/env_1/playlists/playlist_1/local-items",
        json={"audio_file_id": "file_removed"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "audio_file_not_active"


def test_export_apply_run_lookup(api_client: TestClient) -> None:
    container = _container(api_client)
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )
        repositories.environment_repository.save(
            MusicEnvironment(id="env_2", name="Other", root_path=Path("/Volumes/OTHER"))
        )
        repositories.export_plan_repository.save(ExportPlan(id="plan_1", environment_id="env_1"))
        apply_run = ExportApplyRun(
            id="apply_1",
            export_plan_id="plan_1",
            environment_id="env_1",
            status=ExportApplyRunStatus.COMPLETED,
            started_at="2026-05-22T10:00:00+00:00",
            finished_at="2026-05-22T10:00:01+00:00",
            item_results=(
                ExportApplyItemResult(
                    action=ExportAction.CREATE_FOLDER,
                    target_path=Path("/Volumes/USB/_music_manager"),
                    status=ExportApplyItemStatus.SUCCEEDED,
                    created_at="2026-05-22T10:00:00+00:00",
                ),
            ),
        )
        repositories.export_apply_run_repository.save(apply_run)

    ok = api_client.get("/environments/env_1/export-apply-runs/apply_1")
    wrong_environment = api_client.get("/environments/env_2/export-apply-runs/apply_1")

    assert ok.status_code == 200
    assert ok.json()["apply_run_id"] == "apply_1"
    assert wrong_environment.status_code == 400


def test_request_validation_errors_use_stable_shape(api_client: TestClient) -> None:
    response = api_client.post("/environments", json={"name": "Missing root"})

    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_error"
    assert response.json()["message"]


def test_openapi_includes_desktop_readiness_models(api_client: TestClient) -> None:
    schema = api_client.get("/openapi.json").json()

    schemas = schema["components"]["schemas"]
    assert "EnvironmentOverviewRead" in schemas
    assert "PlaylistDetailRead" in schemas
    assert "ApiErrorRead" in schemas
    assert (
        schema["paths"]["/environments/{environment_id}/overview"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/EnvironmentOverviewRead"
    )


def test_full_synchronous_desktop_api_flow(
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    from music_manager_backend.api.app import create_app

    app = create_app(api_settings)
    app.state.container = replace(
        app.state.container,
        soundcloud_playlist_importer=FakeSoundCloudImporter(
            _playlist((_track(1, "Track One", "artist/track-one"),))
        ),
    )
    client = TestClient(app)
    root = tmp_path / "usb"
    library_root = tmp_path / "library"
    root.mkdir()
    library_root.mkdir()
    local_audio = root / "Track One.mp3"
    local_audio.write_bytes(b"fake audio")
    library_audio = library_root / "Track One.mp3"
    library_audio.write_bytes(b"library audio")

    environment = client.post(
        "/environments",
        json={"name": "USB", "root_path": str(root)},
    ).json()
    environment_id = environment["id"]
    scan = client.post(f"/environments/{environment_id}/scan")
    imported = client.post(
        f"/environments/{environment_id}/soundcloud/playlists",
        json={"url": SOURCE_URL},
    ).json()
    detail_before_mapping = client.get(
        f"/environments/{environment_id}/playlists/{imported['playlist_id']}"
    ).json()
    song_id = detail_before_mapping["items"][0]["song_id"]
    with app.state.container.repository_bundle() as repositories:
        repositories.library_repository.save_default(
            MusicLibrary(
                id="default",
                root_path=library_root,
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
        repositories.library_track_repository.save(
            LibraryTrack(
                id="library_track_1",
                library_id="default",
                canonical_path=library_audio,
                filename=library_audio.name,
                size_bytes=library_audio.stat().st_size,
                modified_at=library_audio.stat().st_mtime,
                status=LibraryTrackStatus.ACTIVE,
                title="Track One",
                artist="Artist",
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
    client.post(
        f"/environments/{environment_id}/library/matching/manual-mappings",
        json={"song_id": song_id, "library_track_id": "library_track_1"},
    )
    overview = client.get(f"/environments/{environment_id}/overview")
    detail = client.get(f"/environments/{environment_id}/playlists/{imported['playlist_id']}")
    plan = client.post(f"/environments/{environment_id}/export-plans").json()
    apply_run = client.post(
        f"/environments/{environment_id}/export-plans/{plan['export_plan_id']}/apply"
    ).json()
    fetched_apply_run = _wait_apply_run(client, environment_id, apply_run["apply_run_id"])

    assert scan.status_code == 200
    assert overview.json()["manually_mapped_count"] == 1
    assert detail.json()["items"][0]["accepted_library_track_id"] == "library_track_1"
    assert plan["counts"]["copy_file"] == 1
    assert apply_run["status"] in {"queued", "running", "completed"}
    assert fetched_apply_run["status"] == "completed"
    copy_targets = [
        Path(item["target_path"])
        for item in plan["items"]
        if item["action"] == "copy_file"
    ]
    assert len(copy_targets) == 1
    assert copy_targets[0].read_bytes() == b"library audio"
    assert copy_targets[0].is_relative_to(root)
    assert not copy_targets[0].is_relative_to(root / "_music_manager")


def _container(api_client: TestClient) -> AppContainer:
    app = cast(FastAPI, api_client.app)
    return cast(AppContainer, app.state.container)


def _wait_apply_run(
    client: TestClient,
    environment_id: str,
    apply_run_id: str,
) -> dict[str, object]:
    for _ in range(40):
        response = client.get(f"/environments/{environment_id}/export-apply-runs/{apply_run_id}")
        body = response.json()
        if body["status"] not in {"queued", "running"}:
            return cast(dict[str, object], body)
        sleep(0.05)
    raise AssertionError(f"Apply run did not finish: {apply_run_id}")


def _seed_desktop_view_data(container: AppContainer) -> None:
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )
        repositories.song_repository.save(
            SongMaster(id="song_1", title="Matched", artist="Artist", duration_seconds=180)
        )
        repositories.song_repository.save(
            SongMaster(id="song_2", title="Maybe", artist="Artist", duration_seconds=181)
        )
        repositories.song_repository.save(
            SongMaster(id="song_3", title="Missing", artist="Artist")
        )
        repositories.song_repository.save(SongMaster(id="song_4", title="Old", artist="Artist"))
        repositories.playlist_repository.save(
            Playlist(
                id="playlist_1",
                environment_id="env_1",
                name="Set",
                items=(
                    PlaylistItem(song_id="song_1", position=1),
                    PlaylistItem(song_id="song_2", position=2),
                    PlaylistItem(song_id="song_3", position=3),
                    PlaylistItem(song_id="song_4", position=4, remote_membership_active=False),
                ),
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_1",
                environment_id="env_1",
                path=Path("/Volumes/USB/matched.mp3"),
                size_bytes=1,
                modified_at=1.0,
                title="Matched",
                artist="Artist",
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_2",
                environment_id="env_1",
                path=Path("/Volumes/USB/maybe.mp3"),
                size_bytes=1,
                modified_at=1.0,
                title="Maybe",
                artist="Artist",
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_removed",
                environment_id="env_1",
                path=Path("/Volumes/USB/removed.mp3"),
                size_bytes=1,
                modified_at=1.0,
                status=AudioFileStatus.REMOVED,
            )
        )
        repositories.library_repository.save_default(
            MusicLibrary(
                id="default",
                root_path=Path("/Music/Library"),
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
        repositories.library_track_repository.save(
            LibraryTrack(
                id="library_matched",
                library_id="default",
                canonical_path=Path("/Music/Library/matched.mp3"),
                filename="matched.mp3",
                status=LibraryTrackStatus.ACTIVE,
                title="Matched",
                artist="Artist",
                duration_seconds=180,
                normalized_title="matched",
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
        repositories.library_track_repository.save(
            LibraryTrack(
                id="library_maybe_a",
                library_id="default",
                canonical_path=Path("/Music/Library/maybe-a.mp3"),
                filename="maybe-a.mp3",
                status=LibraryTrackStatus.ACTIVE,
                title="Maybe",
                artist="Artist",
                duration_seconds=181,
                normalized_title="maybe",
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
        repositories.library_track_repository.save(
            LibraryTrack(
                id="library_maybe_b",
                library_id="default",
                canonical_path=Path("/Music/Library/maybe-b.mp3"),
                filename="maybe-b.mp3",
                status=LibraryTrackStatus.ACTIVE,
                title="Maybe",
                artist="Artist",
                duration_seconds=181,
                normalized_title="maybe",
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
        repositories.song_library_link_repository.save(
            SongLibraryLink(
                song_id="song_1",
                library_track_id="library_matched",
                method="library_identity_exact",
                confidence=1.0,
                reviewed=False,
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
        repositories.match_link_repository.save(
            MatchLink(
                song_id="song_1",
                audio_file_id="file_1",
                method="metadata_exact",
                confidence=0.95,
            )
        )


def _playlist(
    tracks: tuple[ParsedSoundCloudTrack, ...],
) -> ParsedSoundCloudPlaylist:
    return ParsedSoundCloudPlaylist(
        source_url=SOURCE_URL,
        title="Funk",
        tracks=tracks,
    )


def _track(position: int, title: str, path: str) -> ParsedSoundCloudTrack:
    artist = path.split("/", maxsplit=1)[0].title()
    return ParsedSoundCloudTrack(
        position=position,
        title=title,
        uploader=artist,
        uploader_url=f"https://soundcloud.com/{path.split('/', maxsplit=1)[0]}",
        canonical_track_url=f"https://soundcloud.com/{path}",
        playlist_track_url=f"https://soundcloud.com/{path}?in=user/sets/funk",
    )
