from music_manager_backend.infrastructure.soundcloud.public_playlist_importer import (
    HttpSoundCloudHtmlFetcher,
)
from music_manager_backend.infrastructure.soundcloud.track_discovery_parser import (
    SoundCloudTrackDiscoveryHtmlParser,
)
from music_manager_backend.ports.soundcloud import SoundCloudHtmlFetcher
from music_manager_backend.ports.soundcloud_discovery import SoundCloudTrackDiscovery


class PublicTrackDiscoveryProvider:
    def __init__(
        self,
        *,
        fetcher: SoundCloudHtmlFetcher | None = None,
        parser: SoundCloudTrackDiscoveryHtmlParser | None = None,
    ) -> None:
        self.fetcher = fetcher or HttpSoundCloudHtmlFetcher()
        self.parser = parser or SoundCloudTrackDiscoveryHtmlParser()

    def discover_track(self, url: str) -> SoundCloudTrackDiscovery:
        html = self.fetcher.fetch(url)
        return self.parser.parse(html, source_url=url)
