from typing import Literal

from pydantic import BaseModel, Field

from music_manager_backend.application.dtos.environment import ScanSummaryRead
from music_manager_backend.application.dtos.soundcloud_discovery import (
    SoundCloudTrackDiscoveryRead,
)


class MatchCandidateRead(BaseModel):
    audio_file_id: str
    path: str
    source_area: Literal["download", "usb", "other"]
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
    source_discovery: SoundCloudTrackDiscoveryRead | None = None


class MatchingRunSummary(BaseModel):
    environment_id: str
    total: int
    matched: int
    missing_audio: int
    ambiguous: int
    manually_mapped: int


class DownloadMatchSummaryRead(BaseModel):
    checked: int
    matched: int
    missing_audio: int
    ambiguous: int
    preserved_reviewed: int


class DownloadMatchRunResultRead(BaseModel):
    environment_id: str
    download_path: str
    scan: ScanSummaryRead
    matching: DownloadMatchSummaryRead


class ManualMappingCreate(BaseModel):
    song_id: str
    audio_file_id: str
