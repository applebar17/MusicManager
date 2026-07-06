from pathlib import Path

from pydantic import BaseModel

from music_manager_backend.domain.entities.library import MusicLibrary


class LibraryConfigure(BaseModel):
    root_path: Path


class LibraryRead(BaseModel):
    configured: bool
    root_path: str | None
    created_at: str | None
    updated_at: str | None
    track_count: int


def library_read(library: MusicLibrary | None, *, track_count: int) -> LibraryRead:
    if library is None:
        return LibraryRead(
            configured=False,
            root_path=None,
            created_at=None,
            updated_at=None,
            track_count=track_count,
        )
    return LibraryRead(
        configured=True,
        root_path=str(library.root_path),
        created_at=library.created_at,
        updated_at=library.updated_at,
        track_count=track_count,
    )
