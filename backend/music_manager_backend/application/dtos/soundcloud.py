from pydantic import BaseModel
from typing import Literal


class SoundCloudPlaylistImportRequest(BaseModel):
    url: str


class SoundCloudPlaylistImportResult(BaseModel):
    environment_id: str
    remote_playlist_id: str
    playlist_id: str
    sync_snapshot_id: str
    playlist_name: str
    track_count: int
    added: int
    removed: int
    reactivated: int
    reordered: int
    metadata_changed: int
    unchanged: int
    warnings: tuple[str, ...] = ()


class SoundCloudPlaylistSyncItemResult(BaseModel):
    playlist_id: str
    remote_playlist_id: str
    source_url: str
    status: Literal["synced", "failed"]
    playlist_name: str | None = None
    track_count: int | None = None
    added: int | None = None
    removed: int | None = None
    reactivated: int | None = None
    reordered: int | None = None
    metadata_changed: int | None = None
    unchanged: int | None = None
    warnings: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None


class SoundCloudPlaylistSyncAllResult(BaseModel):
    environment_id: str
    total: int
    succeeded: int
    failed: int
    results: tuple[SoundCloudPlaylistSyncItemResult, ...]
