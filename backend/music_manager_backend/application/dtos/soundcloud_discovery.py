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
    fetched_at: str | None = None


class SoundCloudSourceSyncItemRead(BaseModel):
    song_id: str
    title: str
    status: str
    source_url: str | None = None
    discovered_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class SoundCloudSourceSyncResultRead(BaseModel):
    environment_id: str
    total: int
    discovered: int
    skipped: int
    failed: int
    results: list[SoundCloudSourceSyncItemRead] = Field(default_factory=list)
