from pydantic import BaseModel


class AudioFileRead(BaseModel):
    id: str
    environment_id: str
    path: str
    size_bytes: int
    modified_at: float
    status: str
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None
