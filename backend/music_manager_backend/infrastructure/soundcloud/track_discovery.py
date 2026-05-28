from music_manager_backend.infrastructure.soundcloud.public_playlist_importer import (
    HttpSoundCloudApiClient,
    HttpSoundCloudHtmlFetcher,
    SoundCloudPublicApiClient,
    _extract_client_id,
)
from music_manager_backend.infrastructure.soundcloud.track_discovery_parser import (
    SoundCloudTrackDiscoveryHtmlParser,
    merge_soundcloud_api_track_discovery,
)
from music_manager_backend.ports.soundcloud import SoundCloudHtmlFetcher
from music_manager_backend.ports.soundcloud_discovery import SoundCloudTrackDiscovery
from music_manager_backend.shared.errors import InfrastructureError


class PublicTrackDiscoveryProvider:
    def __init__(
        self,
        *,
        fetcher: SoundCloudHtmlFetcher | None = None,
        parser: SoundCloudTrackDiscoveryHtmlParser | None = None,
        api_client: SoundCloudPublicApiClient | None = None,
    ) -> None:
        self.fetcher = fetcher or HttpSoundCloudHtmlFetcher()
        self.parser = parser or SoundCloudTrackDiscoveryHtmlParser()
        self.api_client = api_client if api_client is not None else (
            HttpSoundCloudApiClient() if fetcher is None else None
        )

    def discover_track(self, url: str) -> SoundCloudTrackDiscovery:
        html = self.fetcher.fetch(url)
        discovery = self.parser.parse(html, source_url=url)
        return self._enrich_from_api(html=html, url=url, discovery=discovery)

    def _enrich_from_api(
        self,
        *,
        html: str,
        url: str,
        discovery: SoundCloudTrackDiscovery,
    ) -> SoundCloudTrackDiscovery:
        if self.api_client is None:
            return discovery

        try:
            client_id = _extract_client_id(html, api_client=self.api_client)
            if client_id is None:
                return discovery
            api_track = self.api_client.fetch_json(
                "https://api-v2.soundcloud.com/resolve",
                params={"url": url, "client_id": client_id},
            )
        except InfrastructureError:
            return discovery

        if not isinstance(api_track, dict):
            return discovery
        if api_track.get("kind") not in {None, "track"}:
            return discovery
        return merge_soundcloud_api_track_discovery(discovery, api_track)
