from dataclasses import dataclass, field


@dataclass(frozen=True)
class AudioMetadata:
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    duration_seconds: int | None = None
    bpm: int | None = None
    key: str | None = None
    comment: str | None = None
    raw: dict[str, object] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
