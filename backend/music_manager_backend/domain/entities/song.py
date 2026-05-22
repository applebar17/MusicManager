from dataclasses import dataclass


@dataclass(frozen=True)
class SongMaster:
    id: str
    title: str
    artist: str | None = None
    duration_seconds: int | None = None
    source_track_id: str | None = None
    source_url: str | None = None
    local_title_override: str | None = None
    local_artist_override: str | None = None

    @property
    def display_title(self) -> str:
        return self.local_title_override or self.title

    @property
    def display_artist(self) -> str | None:
        return self.local_artist_override or self.artist

