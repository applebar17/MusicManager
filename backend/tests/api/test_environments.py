from pathlib import Path

from fastapi.testclient import TestClient

from music_manager_backend.api.app import create_app
from music_manager_backend.shared.settings import Settings


def test_create_environment_persists_to_sqlite(api_client: TestClient, tmp_path: Path) -> None:
    response = api_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(tmp_path / "usb")},
    )

    assert response.status_code == 200
    created = response.json()
    assert created["name"] == "Gig USB"
    assert created["root_path"] == str(tmp_path / "usb")

    list_response = api_client.get("/environments")
    assert list_response.status_code == 200
    assert list_response.json() == [created]


def test_environment_persists_across_app_recreation(
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    first_client = TestClient(create_app(api_settings))
    create_response = first_client.post(
        "/environments",
        json={"name": "Gig USB", "root_path": str(tmp_path / "usb")},
    )
    created = create_response.json()

    second_client = TestClient(create_app(api_settings))
    list_response = second_client.get("/environments")

    assert list_response.status_code == 200
    assert list_response.json() == [created]
