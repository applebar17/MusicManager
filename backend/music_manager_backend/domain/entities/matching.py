from dataclasses import dataclass
from enum import StrEnum


class MatchStatus(StrEnum):
    MATCHED = "matched"
    MISSING_AUDIO = "missing_audio"
    AMBIGUOUS = "ambiguous"
    MANUALLY_MAPPED = "manually_mapped"


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
