from dataclasses import dataclass, field

from music_manager_backend.ports.soundcloud_discovery import SoundCloudDiscoveryLink


@dataclass(frozen=True)
class SoundCloudSourceDiscovery:
    environment_id: str
    song_id: str
    track_url: str
    fetched_at: str
    track_urn: str | None = None
    title: str | None = None
    artist: str | None = None
    description: str | None = None
    purchase_title: str | None = None
    purchase_url: str | None = None
    downloadable: bool | None = None
    download_url: str | None = None
    links: tuple[SoundCloudDiscoveryLink, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    release_metadata: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    raw: dict[str, object] = field(default_factory=dict)

    @property
    def has_source_link(self) -> bool:
        return self.best_source_url is not None

    @property
    def best_source_url(self) -> str | None:
        if self.download_url:
            return self.download_url
        if self.purchase_url:
            return self.purchase_url
        for link in self.links:
            if link.kind in {"download", "buy", "buy_or_download"}:
                return link.url
        return None
