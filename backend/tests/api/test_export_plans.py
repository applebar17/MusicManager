from pathlib import Path
from time import sleep
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from music_manager_backend.api.container import AppContainer
from music_manager_backend.domain.entities import (
    AudioFile,
    ExportPlan,
    ExportPlanItem,
    MatchLink,
    MusicEnvironment,
    Playlist,
    PlaylistItem,
    SongMaster,
)
from music_manager_backend.domain.entities.export_plan import ExportAction


def test_create_and_get_export_plan(api_client: TestClient, tmp_path: Path) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    source = root / "track.mp3"
    source.write_bytes(b"audio")
    _seed_export_data(container, root=root, source=source)

    create_response = api_client.post("/environments/env_1/export-plans")

    assert create_response.status_code == 200
    body = create_response.json()
    assert body["environment_id"] == "env_1"
    assert body["counts"]["copy_file"] == 1
    assert body["items"][0]["action"] == "create_folder"

    get_response = api_client.get(f"/environments/env_1/export-plans/{body['export_plan_id']}")

    assert get_response.status_code == 200
    assert get_response.json() == body


def test_create_export_plan_accepts_selected_playlists(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    source = root / "track.mp3"
    source.write_bytes(b"audio")
    _seed_export_data(container, root=root, source=source)

    response = api_client.post(
        "/environments/env_1/export-plans",
        json={"playlist_ids": ["playlist_1"]},
    )

    assert response.status_code == 200
    assert response.json()["counts"]["copy_file"] == 1


def test_get_export_plan_rejects_wrong_environment(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    source = root / "track.mp3"
    source.write_bytes(b"audio")
    _seed_export_data(container, root=root, source=source)
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_2", name="Other", root_path=tmp_path / "other")
        )
    create_response = api_client.post("/environments/env_1/export-plans")

    response = api_client.get(
        f"/environments/env_2/export-plans/{create_response.json()['export_plan_id']}"
    )

    assert response.status_code == 400


def test_apply_export_plan_streams_results_and_persists_run(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    source = root / "track.mp3"
    source.write_bytes(b"audio")
    _seed_export_data(container, root=root, source=source)
    create_response = api_client.post("/environments/env_1/export-plans")

    response = api_client.post(
        f"/environments/env_1/export-plans/"
        f"{create_response.json()['export_plan_id']}/apply"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["environment_id"] == "env_1"
    assert body["export_plan_id"] == create_response.json()["export_plan_id"]
    assert body["status"] in {"queued", "running", "completed"}
    final = _wait_apply_run(api_client, body["apply_run_id"])
    assert final["status"] == "completed"
    assert final["counts"]["succeeded"] >= 1
    assert (root / "Set" / "track.mp3").read_bytes() == b"audio"
    with container.repository_bundle() as repositories:
        assert repositories.export_apply_run_repository.get(body["apply_run_id"]) is not None


def test_apply_export_plan_can_copy_matched_download_source_outside_usb_root(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    downloads = tmp_path / "downloads"
    root.mkdir()
    downloads.mkdir()
    source = downloads / "track.mp3"
    source.write_bytes(b"audio")
    _seed_export_data(container, root=root, source=source, download_path=downloads)
    create_response = api_client.post("/environments/env_1/export-plans")

    response = api_client.post(
        f"/environments/env_1/export-plans/"
        f"{create_response.json()['export_plan_id']}/apply"
    )

    assert response.status_code == 200
    _wait_apply_run(api_client, response.json()["apply_run_id"])
    assert (root / "Set" / "track.mp3").read_bytes() == b"audio"
    assert source.exists()


def test_update_export_plan_reorders_and_excludes_items(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    source = root / "track.mp3"
    source.write_bytes(b"audio")
    _seed_export_data(container, root=root, source=source)
    create_response = api_client.post("/environments/env_1/export-plans")
    plan = create_response.json()
    copy_item = next(item for item in plan["items"] if item["action"] == "copy_file")
    included = [item["export_plan_item_id"] for item in plan["items"]]
    excluded = [copy_item["export_plan_item_id"]]
    included = [item_id for item_id in included if item_id not in excluded]

    response = api_client.patch(
        f"/environments/env_1/export-plans/{plan['export_plan_id']}",
        json={"included_item_ids": included, "excluded_item_ids": excluded},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"].get("copy_file", 0) == 0
    updated_copy = next(
        item
        for item in body["items"]
        if item["export_plan_item_id"] == copy_item["export_plan_item_id"]
    )
    assert updated_copy["included"] is False


def test_invalid_export_plan_is_saved_but_apply_is_blocked(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    source = root / "track.mp3"
    source.write_bytes(b"audio")
    _seed_export_data(container, root=root, source=source)
    plan = api_client.post("/environments/env_1/export-plans").json()
    copy_item = next(item for item in plan["items"] if item["action"] == "copy_file")
    folder_item = next(
        item
        for item in plan["items"]
        if item["action"] == "create_folder" and item["target_path"].endswith("Set")
    )
    included = [
        item["export_plan_item_id"]
        for item in plan["items"]
        if item["export_plan_item_id"] != folder_item["export_plan_item_id"]
    ]

    update_response = api_client.patch(
        f"/environments/env_1/export-plans/{plan['export_plan_id']}",
        json={
            "included_item_ids": included,
            "excluded_item_ids": [folder_item["export_plan_item_id"]],
        },
    )
    apply_response = api_client.post(
        f"/environments/env_1/export-plans/{plan['export_plan_id']}/apply"
    )

    assert update_response.status_code == 200
    assert update_response.json()["is_valid"] is False
    assert any(
        error["export_plan_item_id"] == copy_item["export_plan_item_id"]
        for error in update_response.json()["validation_errors"]
    )
    assert apply_response.status_code == 400


def test_export_plan_cannot_be_edited_after_apply_starts(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    source = root / "track.mp3"
    source.write_bytes(b"audio")
    _seed_export_data(container, root=root, source=source)
    plan = api_client.post("/environments/env_1/export-plans").json()

    apply_response = api_client.post(
        f"/environments/env_1/export-plans/{plan['export_plan_id']}/apply"
    )
    _wait_apply_run(api_client, apply_response.json()["apply_run_id"])
    response = api_client.patch(
        f"/environments/env_1/export-plans/{plan['export_plan_id']}",
        json={
            "included_item_ids": [item["export_plan_item_id"] for item in plan["items"]],
            "excluded_item_ids": [],
        },
    )

    assert apply_response.status_code == 200
    assert response.status_code == 400


def test_apply_export_plan_rejects_missing_plan(api_client: TestClient, tmp_path: Path) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=root)
        )

    response = api_client.post("/environments/env_1/export-plans/missing/apply")

    assert response.status_code == 404


def test_apply_export_plan_rejects_unsafe_plan(api_client: TestClient, tmp_path: Path) -> None:
    container = _container(api_client)
    root = tmp_path / "usb"
    root.mkdir()
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=root)
        )
        repositories.export_plan_repository.save(
            ExportPlan(
                id="plan_1",
                environment_id="env_1",
                items=(
                    ExportPlanItem(
                        action=ExportAction.CREATE_FOLDER,
                        target_path=tmp_path / "outside",
                    ),
                ),
            )
        )

    response = api_client.post("/environments/env_1/export-plans/plan_1/apply")

    assert response.status_code == 400


def _seed_export_data(
    container: AppContainer,
    *,
    root: Path,
    source: Path,
    download_path: Path | None = None,
) -> None:
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(
                id="env_1",
                name="USB",
                root_path=root,
                download_path=download_path,
            )
        )
        repositories.song_repository.save(
            SongMaster(id="song_1", title="Track", artist="Artist")
        )
        repositories.playlist_repository.save(
            Playlist(
                id="playlist_1",
                environment_id="env_1",
                name="Set",
                items=(PlaylistItem(song_id="song_1", position=1),),
            )
        )
        repositories.audio_file_repository.save(
            AudioFile(
                id="file_1",
                environment_id="env_1",
                path=source,
                size_bytes=1,
                modified_at=1.0,
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


def _container(api_client: TestClient) -> AppContainer:
    app = cast(FastAPI, api_client.app)
    return cast(AppContainer, app.state.container)


def _wait_apply_run(api_client: TestClient, apply_run_id: str) -> dict[str, object]:
    for _ in range(40):
        response = api_client.get(f"/environments/env_1/export-apply-runs/{apply_run_id}")
        body = response.json()
        if body["status"] not in {"queued", "running"}:
            return cast(dict[str, object], body)
        sleep(0.05)
    raise AssertionError(f"Apply run did not finish: {apply_run_id}")
