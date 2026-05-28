from dataclasses import replace
from pathlib import Path
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
    MatchLink,
    MusicEnvironment,
    Playlist,
    PlaylistItem,
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
    assert overview["unique_song_count"] == 4
    assert overview["active_audio_file_count"] == 2
    assert overview["removed_audio_file_count"] == 1
    assert overview["unmanaged_audio_file_count"] == 1
    assert overview["matched_count"] == 1
    assert overview["missing_audio_count"] == 2
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
        "song_4",
    ]
    assert detail["items"][0]["match_status"] == "matched"
    assert detail["items"][0]["accepted_audio_file_id"] == "file_1"
    assert detail["items"][0]["accepted_audio_filename"] == "matched.mp3"
    assert detail["items"][0]["accepted_audio_relative_path"] == "matched.mp3"
    assert detail["items"][0]["playback_url"] == (
        "/environments/env_1/playback/audio-files/file_1"
    )
    assert detail["items"][1]["match_status"] == "ambiguous"
    assert detail["items"][3]["remote_membership_active"] is False


def test_playlist_detail_rejects_wrong_environment(api_client: TestClient) -> None:
    container = _container(api_client)
    _seed_desktop_view_data(container)
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_2", name="Other", root_path=Path("/Volumes/OTHER"))
        )

    response = api_client.get("/environments/env_2/playlists/playlist_1")

    assert response.status_code == 404


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
                    target_path=Path("/Volumes/USB/.music_manager"),
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
    root.mkdir()
    local_audio = root / "Track One.mp3"
    local_audio.write_bytes(b"fake audio")

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
    client.post(f"/environments/{environment_id}/matching/run")
    detail_before_mapping = client.get(
        f"/environments/{environment_id}/playlists/{imported['playlist_id']}"
    ).json()
    audio_file_id = client.get(f"/environments/{environment_id}/audio-files").json()[0]["id"]
    song_id = detail_before_mapping["items"][0]["song_id"]
    client.post(
        f"/environments/{environment_id}/matching/manual-mappings",
        json={"song_id": song_id, "audio_file_id": audio_file_id},
    )
    overview = client.get(f"/environments/{environment_id}/overview")
    detail = client.get(f"/environments/{environment_id}/playlists/{imported['playlist_id']}")
    plan = client.post(f"/environments/{environment_id}/export-plans").json()
    apply_run = client.post(
        f"/environments/{environment_id}/export-plans/{plan['export_plan_id']}/apply"
    ).json()
    fetched_apply_run = client.get(
        f"/environments/{environment_id}/export-apply-runs/{apply_run['apply_run_id']}"
    )

    assert scan.status_code == 200
    assert overview.json()["manually_mapped_count"] == 1
    assert detail.json()["items"][0]["playback_url"].endswith(audio_file_id)
    assert plan["counts"]["copy_file"] == 1
    assert apply_run["status"] == "completed"
    assert fetched_apply_run.status_code == 200
    copy_targets = [
        Path(item["target_path"])
        for item in plan["items"]
        if item["action"] == "copy_file"
    ]
    assert len(copy_targets) == 1
    assert copy_targets[0].read_bytes() == b"fake audio"
    assert copy_targets[0].is_relative_to(root)
    assert not copy_targets[0].is_relative_to(root / ".music_manager")


def _container(api_client: TestClient) -> AppContainer:
    app = cast(FastAPI, api_client.app)
    return cast(AppContainer, app.state.container)


def _seed_desktop_view_data(container: AppContainer) -> None:
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )
        repositories.song_repository.save(
            SongMaster(id="song_1", title="Matched", artist="Artist")
        )
        repositories.song_repository.save(SongMaster(id="song_2", title="Maybe", artist="Artist"))
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
