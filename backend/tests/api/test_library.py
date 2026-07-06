from pathlib import Path

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
