import httpx

from music_manager_backend.infrastructure.soundcloud.public_html_parser import (
    PublicPlaylistHtmlParser,
)
from music_manager_backend.ports.soundcloud import SoundCloudHtmlFetcher
from music_manager_backend.ports.soundcloud_models import ParsedSoundCloudPlaylist
from music_manager_backend.shared.errors import InfrastructureError

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; MusicManager/0.1; "
    "+https://github.com/local/music-manager)"
)


class HttpSoundCloudHtmlFetcher:
    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, url: str) -> str:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout_seconds,
                headers={"User-Agent": DEFAULT_USER_AGENT},
            ) as client:
                response = client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise InfrastructureError(
                f"Could not fetch SoundCloud public playlist: {url}",
                code="soundcloud_public_fetch_failed",
            ) from exc

        return response.text


class PublicPlaylistImporter:
    def __init__(
        self,
        *,
        fetcher: SoundCloudHtmlFetcher | None = None,
        parser: PublicPlaylistHtmlParser | None = None,
    ) -> None:
        self.fetcher = fetcher or HttpSoundCloudHtmlFetcher()
        self.parser = parser or PublicPlaylistHtmlParser()

    def import_playlist(self, url: str) -> ParsedSoundCloudPlaylist:
        html = self.fetcher.fetch(url)
        return self.parser.parse(html, source_url=url)
