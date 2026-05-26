from pydantic import BaseModel, Field


class UsbMatchedSongRead(BaseModel):
    song_id: str
    title: str
    artist: str | None = None
    duration_seconds: int | None = None
    playlists: list[str] = Field(default_factory=list)
    method: str
    confidence: float
    reviewed: bool


class UsbFileRead(BaseModel):
    audio_file_id: str
    environment_id: str
    path: str
    relative_path: str
    folder_parts: list[str] = Field(default_factory=list)
    filename: str
    audio_status: str
    match_status: str
    warnings: list[str] = Field(default_factory=list)
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    duration_seconds: int | None = None
    bpm: int | None = None
    key: str | None = None
    comment: str | None = None
    size_bytes: int
    modified_at: float
    matched_song: UsbMatchedSongRead | None = None


class UsbSongCandidateRead(BaseModel):
    song_id: str
    title: str
    artist: str | None = None
    duration_seconds: int | None = None
    playlists: list[str] = Field(default_factory=list)
    status: str
    method: str | None = None
    confidence: float
