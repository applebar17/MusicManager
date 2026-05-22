from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedSoundCloudTrack:
    position: int
    title: str
    uploader: str | None
    uploader_url: str | None
    canonical_track_url: str
    playlist_track_url: str
    artwork_url: str | None = None
    play_count: int | None = None
    duration_seconds: int | None = None
    raw: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedSoundCloudPlaylist:
    source_url: str
    title: str | None
    tracks: tuple[ParsedSoundCloudTrack, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
