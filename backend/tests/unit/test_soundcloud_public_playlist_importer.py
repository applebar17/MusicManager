import pytest

from music_manager_backend.infrastructure.soundcloud.public_playlist_importer import (
    PublicPlaylistImporter,
)
from music_manager_backend.shared.errors import InfrastructureError

SOURCE_URL = "https://soundcloud.com/riccardo-tordini/sets/21_futurfunk_nudisco"


class FakeFetcher:
    def __init__(self, html: str) -> None:
        self.html = html
        self.requested_urls: list[str] = []

    def fetch(self, url: str) -> str:
        self.requested_urls.append(url)
        return self.html


class FailingFetcher:
    def fetch(self, url: str) -> str:
        raise InfrastructureError(
            f"Could not fetch {url}",
            code="soundcloud_public_fetch_failed",
        )


class FakeApiClient:
    def __init__(self) -> None:
        self.text_urls: list[str] = []
        self.json_urls: list[str] = []
        self.track_lookup_ids: list[list[str]] = []

    def fetch_text(self, url: str) -> str:
        self.text_urls.append(url)
        return 'window.config={client_id:"client12345678901234567890"};'

    def fetch_json(self, url: str, *, params: dict[str, str]) -> dict[str, object] | list[object]:
        self.json_urls.append(url)
        if url.endswith("/playlists/2041120920"):
            return {
                "title": "API Set",
                "track_count": 2,
                "tracks": [
                    {
                        "id": 1,
                        "title": "Hydrated One",
                        "permalink_url": "https://soundcloud.com/artist/one",
                        "full_duration": 101000,
                        "user": {
                            "username": "Artist",
                            "permalink_url": "https://soundcloud.com/artist",
                        },
                    },
                    {"id": 2, "kind": "track", "monetization_model": "BLACKBOX"},
                ],
            }
        if url.endswith("/tracks"):
            ids = params["ids"].split(",")
            self.track_lookup_ids.append(ids)
            return [
                {
                    "id": int(track_id),
                    "title": f"Hydrated {track_id}",
                    "permalink_url": f"https://soundcloud.com/artist/{track_id}",
                    "full_duration": int(track_id) * 1000,
                    "user": {
                        "username": "Artist",
                        "permalink_url": "https://soundcloud.com/artist",
                    },
                }
                for track_id in ids
            ]
        raise AssertionError(f"unexpected URL: {url}")


class LargePlaylistApiClient(FakeApiClient):
    def fetch_json(self, url: str, *, params: dict[str, str]) -> dict[str, object] | list[object]:
        if url.endswith("/playlists/2041120920"):
            return {
                "title": "Large API Set",
                "track_count": 56,
                "tracks": [
                    {
                        "id": 1,
                        "title": "Hydrated One",
                        "permalink_url": "https://soundcloud.com/artist/one",
                        "full_duration": 101000,
                        "user": {"username": "Artist"},
                    },
                    *[
                        {"id": track_id, "kind": "track", "monetization_model": "BLACKBOX"}
                        for track_id in range(2, 57)
                    ],
                ],
            }
        return super().fetch_json(url, params=params)


def _incomplete_hydration_html(track_count: int = 2) -> str:
    return f"""
    <html>
      <head>
        <meta property="og:title" content="HTML Set | SoundCloud">
        <meta property="al:web:url" content="soundcloud://playlists:2041120920">
        <script src="https://a-v2.sndcdn.com/assets/app.js"></script>
      </head>
      <body>
        <script>
          window.__sc_hydration = [
            {{
              "hydratable": "playlist",
              "data": {{
                "track_count": {track_count},
                "tracks": [
                  {{
                    "id": 1,
                    "title": "Hydrated One",
                    "permalink_url": "https://soundcloud.com/artist/one",
                    "user": {{"username": "Artist"}}
                  }},
                  {",".join(
                      f'{{"id": {track_id}, "kind": "track", "monetization_model": "BLACKBOX"}}'
                      for track_id in range(2, track_count + 1)
                  )}
                ]
              }}
            }}
          ];
        </script>
      </body>
    </html>
    """


def test_importer_fetches_url_and_parses_playlist() -> None:
    fetcher = FakeFetcher(
        """
        <html>
          <head><meta property="og:title" content="Public Set | SoundCloud"></head>
          <body>
            <li class="trackList__item">
              <span class="trackItem__number"><span class="trackItem__separator">4</span></span>
              <a class="trackItem__username" href="/artist">Artist</a>
              <a class="trackItem__trackTitle" href="/artist/song?in=user/sets/public-set">Song</a>
            </li>
            <div class="paging-eof"></div>
          </body>
        </html>
        """
    )

    playlist = PublicPlaylistImporter(fetcher=fetcher).import_playlist(SOURCE_URL)

    assert fetcher.requested_urls == [SOURCE_URL]
    assert playlist.source_url == SOURCE_URL
    assert playlist.title == "Public Set"
    assert playlist.tracks[0].position == 4
    assert playlist.tracks[0].canonical_track_url == "https://soundcloud.com/artist/song"


def test_importer_enriches_incomplete_hydration_with_public_api() -> None:
    html = _incomplete_hydration_html()
    api_client = FakeApiClient()

    playlist = PublicPlaylistImporter(
        fetcher=FakeFetcher(html),
        api_client=api_client,
    ).import_playlist(SOURCE_URL)

    assert api_client.text_urls == ["https://a-v2.sndcdn.com/assets/app.js"]
    assert api_client.json_urls == [
        "https://api-v2.soundcloud.com/playlists/2041120920",
        "https://api-v2.soundcloud.com/tracks",
    ]
    assert playlist.title == "API Set"
    assert [track.title for track in playlist.tracks] == ["Hydrated One", "Hydrated 2"]
    assert [track.position for track in playlist.tracks] == [1, 2]
    assert [track.duration_seconds for track in playlist.tracks] == [101, 2]
    assert playlist.warnings == ("soundcloud_api_enrichment_used",)


def test_importer_chunks_large_public_api_track_lookups() -> None:
    api_client = LargePlaylistApiClient()

    playlist = PublicPlaylistImporter(
        fetcher=FakeFetcher(_incomplete_hydration_html(track_count=56)),
        api_client=api_client,
    ).import_playlist(SOURCE_URL)

    assert len(playlist.tracks) == 56
    assert [len(ids) for ids in api_client.track_lookup_ids] == [50, 5]
    assert playlist.tracks[50].title == "Hydrated 51"
    assert playlist.tracks[55].title == "Hydrated 56"
    assert playlist.warnings == ("soundcloud_api_enrichment_used",)


def test_importer_surfaces_fetch_failures() -> None:
    with pytest.raises(InfrastructureError) as error:
        PublicPlaylistImporter(fetcher=FailingFetcher()).import_playlist(SOURCE_URL)

    assert error.value.code == "soundcloud_public_fetch_failed"
