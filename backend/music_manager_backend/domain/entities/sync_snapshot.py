from dataclasses import dataclass, field

from music_manager_backend.shared.time import utc_now_iso


@dataclass(frozen=True)
class SyncSnapshot:
    id: str
    source: str
    remote_playlist_id: str
    payload: dict[str, object]
    captured_at: str = field(default_factory=utc_now_iso)
