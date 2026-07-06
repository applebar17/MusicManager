from pydantic import BaseModel, Field

from music_manager_backend.application.dtos.soundcloud_discovery import (
    SoundCloudTrackDiscoveryRead,
)


class PlaylistSummaryRead(BaseModel):
    id: str
    name: str
    remote_playlist_id: str | None = None
    active_item_count: int
    inactive_item_count: int
    matched_count: int
    missing_audio_count: int
    ambiguous_count: int
    manually_mapped_count: int


class PlaylistItemRead(BaseModel):
    song_id: str
    position: int
    title: str
    artist: str | None = None
    duration_seconds: int | None = None
    remote_membership_active: bool
    local_membership_active: bool
    added_by_local_audio_file_id: str | None = None
    remote_removed_at: str | None = None
    match_status: str
    accepted_audio_file_id: str | None = None
    accepted_audio_filename: str | None = None
    accepted_audio_relative_path: str | None = None
    accepted_audio_warnings: list[str] = Field(default_factory=list)
    library_match_status: str | None = None
    accepted_library_track_id: str | None = None
    accepted_library_filename: str | None = None
    accepted_library_path: str | None = None
    playback_url: str | None = None
    source_discovery: SoundCloudTrackDiscoveryRead | None = None


class PlaylistDetailRead(BaseModel):
    id: str
    environment_id: str
    name: str
    remote_playlist_id: str | None = None
    active_item_count: int
    inactive_item_count: int
    items: list[PlaylistItemRead]
    removed_items: list[PlaylistItemRead] = Field(default_factory=list)


class PlaylistLocalItemCreate(BaseModel):
    audio_file_id: str
