from pydantic import BaseModel, Field


class MatchCandidateRead(BaseModel):
    audio_file_id: str
    path: str
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None
    method: str
    confidence: float
    warnings: list[str] = Field(default_factory=list)


class MatchReviewRow(BaseModel):
    song_id: str
    title: str
    artist: str | None = None
    duration_seconds: int | None = None
    status: str
    match: MatchCandidateRead | None = None
    candidates: list[MatchCandidateRead] = []


class MatchingRunSummary(BaseModel):
    environment_id: str
    total: int
    matched: int
    missing_audio: int
    ambiguous: int
    manually_mapped: int


class ManualMappingCreate(BaseModel):
    song_id: str
    audio_file_id: str
