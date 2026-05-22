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

