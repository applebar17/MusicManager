from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from music_manager_backend.api.app import create_app
from music_manager_backend.infrastructure.persistence import (
    SqlitePlaylistRepository,
    SqliteRemotePlaylistRepository,
)
from music_manager_backend.infrastructure.persistence.sqlite import connect
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


def test_import_soundcloud_playlist_persists_data(
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    app = create_app(api_settings)
    app.state.container = replace(
        app.state.container,
        soundcloud_playlist_importer=FakeSoundCloudImporter(
            _playlist(
                (
                    _track(1, "One", "artist/one"),
                    _track(2, "Two", "artist/two"),
                ),
                warnings=("soundcloud_public_html_missing_playlist_title",),
            )
        ),
    )
    client = TestClient(app)
    root = tmp_path / "usb"
    root.mkdir()
    environment_id = client.post(
        "/environments",
        json={"name": "USB", "root_path": str(root)},
    ).json()["id"]

    response = client.post(
        f"/environments/{environment_id}/soundcloud/playlists",
        json={"url": SOURCE_URL},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["playlist_name"] == "Funk"
    assert body["track_count"] == 2
    assert body["added"] == 2
    assert body["warnings"] == ["soundcloud_public_html_missing_playlist_title"]
    assert app.state.container.remote_playlist_repository.get(
        body["remote_playlist_id"]
    ).source_url == SOURCE_URL
    assert app.state.container.playlist_repository.get(body["playlist_id"]).items[0].position == 1


def test_import_soundcloud_playlist_missing_environment_returns_404(
    api_settings: Settings,
) -> None:
    app = create_app(api_settings)
    app.state.container = replace(
        app.state.container,
        soundcloud_playlist_importer=FakeSoundCloudImporter(
            _playlist((_track(1, "One", "a/one"),))
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/environments/env_missing/soundcloud/playlists",
        json={"url": SOURCE_URL},
    )

    assert response.status_code == 404


def test_import_soundcloud_playlist_zero_tracks_returns_400(
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    app = create_app(api_settings)
    app.state.container = replace(
        app.state.container,
        soundcloud_playlist_importer=FakeSoundCloudImporter(_playlist(())),
    )
    client = TestClient(app)
    root = tmp_path / "usb"
    root.mkdir()
    environment_id = client.post(
        "/environments",
        json={"name": "USB", "root_path": str(root)},
    ).json()["id"]

    response = client.post(
        f"/environments/{environment_id}/soundcloud/playlists",
        json={"url": SOURCE_URL},
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "soundcloud_playlist_no_tracks",
        "message": (
            "No tracks were found for this SoundCloud playlist. If the playlist is private, "
            "make it public and try again."
        ),
    }


def test_imported_playlist_survives_app_recreation(
    api_settings: Settings,
    tmp_path: Path,
) -> None:
    first_app = create_app(api_settings)
    first_app.state.container = replace(
        first_app.state.container,
        soundcloud_playlist_importer=FakeSoundCloudImporter(
            _playlist((_track(1, "One", "a/one"),))
        ),
    )
    client = TestClient(first_app)
    root = tmp_path / "usb"
    root.mkdir()
    environment_id = client.post(
        "/environments",
        json={"name": "USB", "root_path": str(root)},
    ).json()["id"]
    response = client.post(
        f"/environments/{environment_id}/soundcloud/playlists",
        json={"url": SOURCE_URL},
    )

    connection = connect(api_settings.database_path)
    try:
        remote = SqliteRemotePlaylistRepository(connection).get(
            response.json()["remote_playlist_id"]
        )
        playlist = SqlitePlaylistRepository(connection).get(response.json()["playlist_id"])
    finally:
        connection.close()

    assert remote is not None
    assert playlist is not None
    assert remote.source_url == SOURCE_URL
    assert playlist.environment_id == environment_id


def _playlist(
    tracks: tuple[ParsedSoundCloudTrack, ...],
    warnings: tuple[str, ...] = (),
) -> ParsedSoundCloudPlaylist:
    return ParsedSoundCloudPlaylist(
        source_url=SOURCE_URL,
        title="Funk",
        tracks=tracks,
        warnings=warnings,
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
