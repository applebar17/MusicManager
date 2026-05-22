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


def test_importer_surfaces_fetch_failures() -> None:
    with pytest.raises(InfrastructureError) as error:
        PublicPlaylistImporter(fetcher=FailingFetcher()).import_playlist(SOURCE_URL)

    assert error.value.code == "soundcloud_public_fetch_failed"
