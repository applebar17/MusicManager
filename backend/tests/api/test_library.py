from pathlib import Path
import json

from fastapi.testclient import TestClient


def test_get_library_returns_unconfigured_by_default(api_client: TestClient) -> None:
    response = api_client.get("/library")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "root_path": None,
        "created_at": None,
        "updated_at": None,
        "track_count": 0,
        "missing_track_count": 0,
        "metadata_asset_count": 0,
        "metadata_index_entry_count": 0,
        "last_metadata_imported_at": None,
    }


def test_configure_library_persists_existing_folder(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    library_root = tmp_path / "library"
    library_root.mkdir()

    response = api_client.put("/library", json={"root_path": str(library_root)})
    get_response = api_client.get("/library")

    assert response.status_code == 200
    configured = response.json()
    assert configured["configured"] is True
    assert configured["root_path"] == str(library_root)
    assert configured["track_count"] == 0
    assert configured["missing_track_count"] == 0
    assert configured["metadata_asset_count"] == 0
    assert configured["metadata_index_entry_count"] == 0
    assert configured["last_metadata_imported_at"] is None
    assert configured["created_at"] is not None
    assert configured["updated_at"] is not None
    assert get_response.json() == configured


def test_configure_library_rejects_invalid_paths(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    missing_response = api_client.put(
        "/library",
        json={"root_path": str(tmp_path / "missing")},
    )
    file_path = tmp_path / "file.txt"
    file_path.write_text("not a directory", encoding="utf-8")
    file_response = api_client.put("/library", json={"root_path": str(file_path)})

    assert missing_response.status_code == 400
    assert missing_response.json()["code"] == "validation_error"
    assert file_response.status_code == 400
    assert file_response.json()["code"] == "validation_error"


def test_scan_library_rejects_unconfigured_library(api_client: TestClient) -> None:
    response = api_client.post("/library/scan")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_library_inventory_rejects_unconfigured_library(api_client: TestClient) -> None:
    response = api_client.get("/library/tracks")

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_align_library_from_environment_copies_usb_audio_and_persists_latest_run(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    library_root = tmp_path / "library"
    environment_root = tmp_path / "usb"
    library_root.mkdir()
    environment_root.mkdir()
    (environment_root / "track.mp3").write_bytes(b"fake audio")
    api_client.put("/library", json={"root_path": str(library_root)})
    environment_id = api_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(environment_root)},
    ).json()["id"]

    response = api_client.post(f"/environments/{environment_id}/library/align")
    latest_response = api_client.get("/library/alignment-runs/latest")

    assert response.status_code == 200
    run = response.json()
    assert run["environment_id"] == environment_id
    assert run["scanned_usb_count"] == 1
    assert run["copied_count"] == 1
    assert run["warning_count"] == 1
    assert run["metadata_import"] is not None
    assert (library_root / "track.mp3").exists()
    assert latest_response.json()["run_id"] == run["run_id"]
    tracks_response = api_client.get("/library/tracks")
    assert tracks_response.status_code == 200
    tracks = tracks_response.json()
    assert tracks[0]["filename"] == "track.mp3"
    assert tracks[0]["status"] == "active"
    assert tracks[0]["mapped_song_count"] == 0


def test_metadata_import_endpoint_and_latest_summary(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    library_root = tmp_path / "library"
    environment_root = tmp_path / "usb"
    library_root.mkdir()
    environment_root.mkdir()
    (environment_root / "tracks.json").write_text(
        json.dumps([{"id": "track_1", "title": "Track"}]),
        encoding="utf-8",
    )
    api_client.put("/library", json={"root_path": str(library_root)})
    environment_id = api_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(environment_root)},
    ).json()["id"]

    response = api_client.post(f"/environments/{environment_id}/library/metadata/import")
    latest_response = api_client.get("/library/metadata/import-runs/latest")
    library_response = api_client.get("/library")

    assert response.status_code == 200
    body = response.json()
    assert body["asset_count"] == 1
    assert body["index_entry_count"] == 1
    assert latest_response.json()["run_id"] == body["run_id"]
    library = library_response.json()
    assert library["metadata_asset_count"] == 1
    assert library["metadata_index_entry_count"] == 1
    assert library["last_metadata_imported_at"] is not None
    assets_response = api_client.get("/library/metadata/assets")
    entries_response = api_client.get("/library/metadata/index-entries")
    assert assets_response.status_code == 200
    assert entries_response.status_code == 200
    assert assets_response.json()[0]["source_path"].endswith("tracks.json")
    assert entries_response.json()[0]["entry_key"]


def test_metadata_import_rejects_unconfigured_library(api_client: TestClient) -> None:
    response = api_client.post("/environments/env_1/library/metadata/import")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
