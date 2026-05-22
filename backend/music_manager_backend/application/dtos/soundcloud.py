from pydantic import BaseModel


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
