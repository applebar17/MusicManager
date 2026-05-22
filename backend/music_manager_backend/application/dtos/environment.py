from pathlib import Path

from pydantic import BaseModel

from music_manager_backend.domain.entities import MusicEnvironment


class EnvironmentCreate(BaseModel):
    name: str
    root_path: Path
    deprecated_folder_name: str = "_deprecated"


class EnvironmentUpdate(BaseModel):
    name: str | None = None
    root_path: Path | None = None
    deprecated_folder_name: str | None = None


class EnvironmentRead(BaseModel):
    id: str
    name: str
    root_path: str
    deprecated_folder_name: str
    archived_at: str | None = None


class ScanSummaryRead(BaseModel):
    scan_run_id: str
    environment_id: str
    added: int
    changed: int
    removed: int
    moved: int
    unchanged: int
    total_active: int


class EnvironmentOverviewRead(BaseModel):
    environment_id: str
    playlist_count: int
    active_playlist_item_count: int
    inactive_playlist_item_count: int
    unique_song_count: int
    active_audio_file_count: int
    removed_audio_file_count: int
    unmanaged_audio_file_count: int
    matched_count: int
    missing_audio_count: int
    ambiguous_count: int
    manually_mapped_count: int


def environment_read(environment: MusicEnvironment) -> EnvironmentRead:
    return EnvironmentRead(
        id=environment.id,
        name=environment.name,
        root_path=str(environment.root_path),
        deprecated_folder_name=environment.deprecated_folder_name,
        archived_at=environment.archived_at,
    )
