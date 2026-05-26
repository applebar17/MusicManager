from pathlib import Path
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from music_manager_backend.api.app import create_app
from music_manager_backend.shared.settings import Settings


def test_create_environment_persists_to_sqlite(api_client: TestClient, tmp_path: Path) -> None:
    root_path = tmp_path / "usb"
    root_path.mkdir()
    response = api_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(root_path)},
    )

    assert response.status_code == 200
    created = response.json()
    assert created["name"] == "Gig USB"
    assert created["root_path"] == str(root_path)

    list_response = api_client.get("/environments")
    assert list_response.status_code == 200
    assert list_response.json() == [created]


def test_environment_persists_across_app_recreation(
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    root_path = tmp_path / "usb"
    root_path.mkdir()
    first_client = TestClient(create_app(api_settings))
    create_response = first_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(root_path)},
    )
    created = create_response.json()

    second_client = TestClient(create_app(api_settings))
    list_response = second_client.get("/environments")

    assert list_response.status_code == 200
    assert list_response.json() == [created]


def test_create_environment_rejects_invalid_roots(api_client: TestClient, tmp_path: Path) -> None:
    missing_response = api_client.post(
        "/environments",
        json={"name": "Missing", "root_path": str(tmp_path / "missing")},
    )
    file_path = tmp_path / "file.txt"
    file_path.write_text("not a directory", encoding="utf-8")
    file_response = api_client.post(
        "/environments",
        json={"name": "File", "root_path": str(file_path)},
    )

    assert missing_response.status_code == 400
    assert file_response.status_code == 400


def test_update_and_archive_environment(api_client: TestClient, tmp_path: Path) -> None:
    first_root = tmp_path / "usb-1"
    second_root = tmp_path / "usb-2"
    first_root.mkdir()
    second_root.mkdir()
    create_response = api_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(first_root)},
    )
    environment_id = create_response.json()["id"]

    update_response = api_client.patch(
        f"/environments/{environment_id}",
        json={"name": "Backup USB", "root_path": str(second_root)},
    )
    archive_response = api_client.post(f"/environments/{environment_id}/archive")

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Backup USB"
    assert update_response.json()["root_path"] == str(second_root)
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None
    assert api_client.get("/environments").json() == []
    assert len(api_client.get("/environments?include_archived=true").json()) == 1


def test_scan_and_list_audio_files(api_client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "usb"
    root.mkdir()
    track = root / "track.mp3"
    track.write_bytes(b"fake audio")
    create_response = api_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(root)},
    )
    environment_id = create_response.json()["id"]

    scan_response = api_client.post(f"/environments/{environment_id}/scan")
    files_response = api_client.get(f"/environments/{environment_id}/audio-files")
    unmanaged_response = api_client.get(f"/environments/{environment_id}/unmanaged-files")

    assert scan_response.status_code == 200
    assert scan_response.json()["added"] == 1
    assert files_response.status_code == 200
    assert files_response.json()[0]["path"] == str(track)
    assert unmanaged_response.json() == files_response.json()


def test_guarded_environment_operation_returns_409_when_busy(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    root = tmp_path / "usb"
    root.mkdir()
    environment_id = api_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(root)},
    ).json()["id"]
    app = cast(FastAPI, api_client.app)

    with app.state.container.operation_coordinator.guard(
        environment_id=environment_id,
        operation_name="existing operation",
    ):
        response = api_client.post(
            f"/environments/{environment_id}/scan",
            headers={"X-Request-ID": "test-request-id"},
        )

    assert response.status_code == 409
    assert response.json()["code"] == "operation_in_progress"
    assert response.headers["Retry-After"] == "2"
    assert response.headers["X-Request-ID"] == "test-request-id"


def test_removed_audio_files_are_listed_only_when_requested(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    root = tmp_path / "usb"
    root.mkdir()
    track = root / "track.mp3"
    track.write_bytes(b"fake audio")
    environment_id = api_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(root)},
    ).json()["id"]
    api_client.post(f"/environments/{environment_id}/scan")

    track.unlink()
    api_client.post(f"/environments/{environment_id}/scan")

    assert api_client.get(f"/environments/{environment_id}/audio-files").json() == []
    removed = api_client.get(f"/environments/{environment_id}/audio-files?status=removed").json()
    assert len(removed) == 1
    assert removed[0]["status"] == "removed"
