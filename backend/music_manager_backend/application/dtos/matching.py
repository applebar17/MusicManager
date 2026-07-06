from pydantic import BaseModel, Field

from music_manager_backend.application.dtos.soundcloud_discovery import (
    SoundCloudTrackDiscoveryRead,
)


class LibraryTrackCandidateRead(BaseModel):
    library_track_id: str
    path: str
    filename: str
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
    library_status: str | None = None
    library_match: LibraryTrackCandidateRead | None = None
    library_candidates: list[LibraryTrackCandidateRead] = []
    source_discovery: SoundCloudTrackDiscoveryRead | None = None


class LibraryMatchReviewRow(BaseModel):
    song_id: str
    title: str
    artist: str | None = None
    duration_seconds: int | None = None
    status: str
    match: LibraryTrackCandidateRead | None = None
    candidates: list[LibraryTrackCandidateRead] = []


class LibraryMatchingRunSummary(BaseModel):
    environment_id: str
    total: int
    matched: int
    missing_library: int
    ambiguous_library: int
    manually_mapped_library: int


class ManualLibraryMappingCreate(BaseModel):
    song_id: str
    library_track_id: str
