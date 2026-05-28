from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SoundCloudDiscoveryLink:
    url: str
    label: str | None
    kind: str
    source: str


@dataclass(frozen=True)
class SoundCloudTrackDiscovery:
    track_url: str
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


class SoundCloudTrackDiscoveryProvider(Protocol):
    def discover_track(self, url: str) -> SoundCloudTrackDiscovery:
        pass
