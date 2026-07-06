from pathlib import Path

from pydantic import BaseModel

from music_manager_backend.domain.entities.library import (
    LibraryAlignmentItem,
    LibraryAlignmentRun,
    MusicLibrary,
)


class LibraryConfigure(BaseModel):
    root_path: Path


class LibraryRead(BaseModel):
    configured: bool
    root_path: str | None
    created_at: str | None
    updated_at: str | None
    track_count: int
    missing_track_count: int


class LibraryAlignmentItemRead(BaseModel):
    id: str
    status: str
    source_path: str
    target_path: str | None
    library_track_id: str | None
    reason_code: str | None
    reason_message: str | None
    title: str | None
    artist: str | None
    duration_seconds: int | None
    normalized_title: str | None


class LibraryAlignmentRunRead(BaseModel):
    run_id: str
    library_id: str
    environment_id: str
    status: str
    started_at: str
    finished_at: str | None
    scanned_library_count: int
    scanned_usb_count: int
    copied_count: int
    reused_count: int
    updated_count: int
    skipped_collision_count: int
    skipped_error_count: int
    warning_count: int
    items: list[LibraryAlignmentItemRead]


def library_read(
    library: MusicLibrary | None,
    *,
    track_count: int,
    missing_track_count: int = 0,
) -> LibraryRead:
    if library is None:
        return LibraryRead(
            configured=False,
            root_path=None,
            created_at=None,
            updated_at=None,
            track_count=track_count,
            missing_track_count=missing_track_count,
        )
    return LibraryRead(
        configured=True,
        root_path=str(library.root_path),
        created_at=library.created_at,
        updated_at=library.updated_at,
        track_count=track_count,
        missing_track_count=missing_track_count,
    )


def library_alignment_run_read(
    run: LibraryAlignmentRun,
    items: tuple[LibraryAlignmentItem, ...],
) -> LibraryAlignmentRunRead:
    return LibraryAlignmentRunRead(
        run_id=run.id,
        library_id=run.library_id,
        environment_id=run.environment_id,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        scanned_library_count=run.scanned_library_count,
        scanned_usb_count=run.scanned_usb_count,
        copied_count=run.copied_count,
        reused_count=run.reused_count,
        updated_count=run.updated_count,
        skipped_collision_count=run.skipped_collision_count,
        skipped_error_count=run.skipped_error_count,
        warning_count=run.warning_count,
        items=[library_alignment_item_read(item) for item in items],
    )


def library_alignment_item_read(item: LibraryAlignmentItem) -> LibraryAlignmentItemRead:
    return LibraryAlignmentItemRead(
        id=item.id,
        status=item.status.value,
        source_path=str(item.source_path),
        target_path=str(item.target_path) if item.target_path is not None else None,
        library_track_id=item.library_track_id,
        reason_code=item.reason_code,
        reason_message=item.reason_message,
        title=item.title,
        artist=item.artist,
        duration_seconds=item.duration_seconds,
        normalized_title=item.normalized_title,
    )
