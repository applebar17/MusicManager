from dataclasses import replace
from pathlib import Path
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from music_manager_backend.api.container import AppContainer
from music_manager_backend.domain.entities import (
    MusicEnvironment,
    Playlist,
    PlaylistItem,
    SongMaster,
)
from music_manager_backend.ports.soundcloud_discovery import (
    SoundCloudDiscoveryLink,
    SoundCloudTrackDiscovery,
)


class FakeSoundCloudDiscoveryProvider:
    def __init__(self, discovery: SoundCloudTrackDiscovery) -> None:
        self.discovery = discovery
        self.requested_urls: list[str] = []

    def discover_track(self, url: str) -> SoundCloudTrackDiscovery:
        self.requested_urls.append(url)
        return self.discovery


def test_soundcloud_discovery_endpoint_returns_track_source_links(
    api_client: TestClient,
) -> None:
    container = _container(api_client)
    provider = FakeSoundCloudDiscoveryProvider(
        SoundCloudTrackDiscovery(
            track_url="https://soundcloud.com/artist/song",
            track_urn="soundcloud:tracks:123",
            title="Remote Title",
            artist="Uploader",
            description="Support the label.",
            purchase_title="Buy",
            purchase_url="https://label.bandcamp.com/album/song",
            links=(
                SoundCloudDiscoveryLink(
                    url="https://label.bandcamp.com/album/song",
                    label="Buy",
                    kind="buy_or_download",
                    source="purchase_button",
                ),
            ),
            tags=("Techno",),
            release_metadata={"Release date": "3 May 2024"},
            warnings=("promotional_low_quality_notice",),
        )
    )
    cast(FastAPI, api_client.app).state.container = replace(
        container,
        soundcloud_track_discovery_provider=provider,
    )
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )
        repositories.song_repository.save(
            SongMaster(
                id="song_1",
                title="Local Title",
                artist="Artist",
                source_url="https://soundcloud.com/artist/song",
            )
        )
        repositories.playlist_repository.save(
            Playlist(
                id="playlist_1",
                environment_id="env_1",
                name="Set",
                items=(PlaylistItem(song_id="song_1", position=1),),
            )
        )

    response = api_client.get("/environments/env_1/songs/song_1/soundcloud-discovery")

    assert response.status_code == 200
    payload = response.json()
    assert provider.requested_urls == ["https://soundcloud.com/artist/song"]
    assert payload["track_urn"] == "soundcloud:tracks:123"
    assert payload["title"] == "Remote Title"
    assert payload["artist"] == "Uploader"
    assert payload["purchase_url"] == "https://label.bandcamp.com/album/song"
    assert payload["links"][0] == {
        "url": "https://label.bandcamp.com/album/song",
        "label": "Buy",
        "kind": "buy_or_download",
        "source": "purchase_button",
    }
    assert payload["tags"] == ["Techno"]
    assert payload["release_metadata"] == {"Release date": "3 May 2024"}
    assert payload["warnings"] == ["promotional_low_quality_notice"]
    assert payload["fetched_at"] is not None

    with container.repository_bundle() as repositories:
        stored = repositories.source_discovery_repository.get("env_1", "song_1")

    assert stored is not None
    assert stored.purchase_url == "https://label.bandcamp.com/album/song"


def test_sync_missing_soundcloud_sources_persists_unmatched_source_links(
    api_client: TestClient,
) -> None:
    container = _container(api_client)
    provider = FakeSoundCloudDiscoveryProvider(
        SoundCloudTrackDiscovery(
            track_url="https://soundcloud.com/artist/missing-song",
            title="Missing Song",
            artist="Uploader",
            purchase_title="Buy",
            purchase_url="https://label.example/missing-song",
            links=(
                SoundCloudDiscoveryLink(
                    url="https://label.example/missing-song",
                    label="Buy",
                    kind="buy",
                    source="api_purchase_url",
                ),
            ),
        )
    )
    cast(FastAPI, api_client.app).state.container = replace(
        container,
        soundcloud_track_discovery_provider=provider,
    )
    with container.repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )
        repositories.song_repository.save(
            SongMaster(
                id="song_1",
                title="Missing Song",
                artist="Artist",
                source_url="https://soundcloud.com/artist/missing-song",
            )
        )
        repositories.playlist_repository.save(
            Playlist(
                id="playlist_1",
                environment_id="env_1",
                name="Set",
                items=(PlaylistItem(song_id="song_1", position=1),),
            )
        )

    response = api_client.post("/environments/env_1/soundcloud-discovery/sync-missing")

    assert response.status_code == 200
    payload = response.json()
    assert payload["discovered"] == 1
    assert payload["results"][0]["discovered_url"] == "https://label.example/missing-song"

    review_response = api_client.get("/environments/env_1/matching/review")
    playlist_response = api_client.get("/environments/env_1/playlists/playlist_1")

    assert review_response.status_code == 200
    assert playlist_response.status_code == 200
    assert review_response.json()[0]["source_discovery"]["purchase_url"] == (
        "https://label.example/missing-song"
    )
    assert playlist_response.json()["items"][0]["source_discovery"]["purchase_url"] == (
        "https://label.example/missing-song"
    )


def test_soundcloud_discovery_endpoint_rejects_song_outside_environment(
    api_client: TestClient,
) -> None:
    with _container(api_client).repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )
        repositories.song_repository.save(
            SongMaster(
                id="song_1",
                title="Song",
                source_url="https://soundcloud.com/artist/song",
            )
        )

    response = api_client.get("/environments/env_1/songs/song_1/soundcloud-discovery")

    assert response.status_code == 404


def test_soundcloud_discovery_endpoint_rejects_song_without_source_url(
    api_client: TestClient,
) -> None:
    with _container(api_client).repository_bundle() as repositories:
        repositories.environment_repository.save(
            MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
        )
        repositories.song_repository.save(SongMaster(id="song_1", title="Song"))
        repositories.playlist_repository.save(
            Playlist(
                id="playlist_1",
                environment_id="env_1",
                name="Set",
                items=(PlaylistItem(song_id="song_1", position=1),),
            )
        )

    response = api_client.get("/environments/env_1/songs/song_1/soundcloud-discovery")

    assert response.status_code == 400
    assert response.json()["code"] == "song_missing_soundcloud_source_url"


def _container(api_client: TestClient) -> AppContainer:
    app = cast(FastAPI, api_client.app)
    return cast(AppContainer, app.state.container)
