from dataclasses import dataclass
from enum import StrEnum


class MatchStatus(StrEnum):
    MATCHED = "matched"
    MISSING_AUDIO = "missing_audio"
    AMBIGUOUS = "ambiguous"
    MANUALLY_MAPPED = "manually_mapped"


class LibraryMatchStatus(StrEnum):
    LIBRARY_MATCHED = "library_matched"
    MISSING_LIBRARY = "missing_library"
    AMBIGUOUS_LIBRARY = "ambiguous_library"
    MANUALLY_MAPPED_LIBRARY = "manually_mapped_library"


@dataclass(frozen=True)
class MatchLink:
    song_id: str
    audio_file_id: str
    method: str
    confidence: float
    reviewed: bool = False


@dataclass(frozen=True)
class MatchCandidate:
    audio_file_id: str
    method: str
    confidence: float


@dataclass(frozen=True)
class SongLibraryLink:
    song_id: str
    library_track_id: str
    method: str
    confidence: float
    reviewed: bool = False
    created_at: str | None = None
    updated_at: str | None = None
