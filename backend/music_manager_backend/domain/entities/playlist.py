from dataclasses import dataclass, field


@dataclass(frozen=True)
class RemotePlaylist:
    id: str
    source: str
    source_url: str
    name: str


@dataclass(frozen=True)
class PlaylistItem:
    song_id: str
    position: int
    remote_membership_active: bool = True
    local_membership_active: bool = False
    added_by_local_audio_file_id: str | None = None
    remote_removed_at: str | None = None

    @property
    def is_active(self) -> bool:
        return self.remote_membership_active or self.local_membership_active

    @property
    def is_removed_history(self) -> bool:
        return not self.remote_membership_active and not self.local_membership_active


@dataclass(frozen=True)
class Playlist:
    id: str
    environment_id: str
    name: str
    remote_playlist_id: str | None = None
    local_name_override: str | None = None
    items: tuple[PlaylistItem, ...] = field(default_factory=tuple)

    @property
    def display_name(self) -> str:
        return self.local_name_override or self.name

