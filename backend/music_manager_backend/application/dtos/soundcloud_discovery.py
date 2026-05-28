from pydantic import BaseModel, Field


class SoundCloudDiscoveryLinkRead(BaseModel):
    url: str
    label: str | None = None
    kind: str
    source: str


class SoundCloudTrackDiscoveryRead(BaseModel):
    environment_id: str
    song_id: str
    track_url: str
    track_urn: str | None = None
    title: str
    artist: str | None = None
    description: str | None = None
    purchase_title: str | None = None
    purchase_url: str | None = None
    downloadable: bool | None = None
    download_url: str | None = None
    links: list[SoundCloudDiscoveryLinkRead] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    release_metadata: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
