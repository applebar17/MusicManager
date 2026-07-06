from typing import Annotated, Any

from fastapi import APIRouter, Depends

from music_manager_backend.api.dependencies import (
    get_library_alignment_run_repository,
    get_library_repository,
    get_library_track_repository,
    guard_library_operation,
)
from music_manager_backend.application.dtos import (
    ApiErrorRead,
    LibraryAlignmentRunRead,
    LibraryConfigure,
    LibraryRead,
)
from music_manager_backend.application.use_cases.align_library import GetLatestLibraryAlignmentRun
from music_manager_backend.application.use_cases.configure_library import ConfigureLibrary
from music_manager_backend.application.use_cases.get_library import GetLibrary
from music_manager_backend.application.use_cases.scan_library import ScanLibrary
from music_manager_backend.infrastructure.audio import MetadataReader
from music_manager_backend.ports.repositories import (
    LibraryAlignmentRunRepository,
    LibraryRepository,
    LibraryTrackRepository,
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorRead},
    404: {"model": ApiErrorRead},
    409: {"model": ApiErrorRead},
    422: {"model": ApiErrorRead},
}

router = APIRouter(prefix="/library", tags=["library"])

LibraryRepositoryDependency = Annotated[
    LibraryRepository,
    Depends(get_library_repository),
]
LibraryTrackRepositoryDependency = Annotated[
    LibraryTrackRepository,
    Depends(get_library_track_repository),
]
LibraryAlignmentRunRepositoryDependency = Annotated[
    LibraryAlignmentRunRepository,
    Depends(get_library_alignment_run_repository),
]


@router.get("", response_model=LibraryRead, responses=ERROR_RESPONSES)
def get_library(
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
) -> LibraryRead:
    return GetLibrary(libraries, library_tracks).execute()


@router.put("", response_model=LibraryRead, responses=ERROR_RESPONSES)
def configure_library(
    data: LibraryConfigure,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
) -> LibraryRead:
    return ConfigureLibrary(libraries, library_tracks).execute(data)


@router.post(
    "/scan",
    response_model=LibraryRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_library_operation("scan_library"))],
)
def scan_library(
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
) -> LibraryRead:
    return ScanLibrary(
        libraries=libraries,
        library_tracks=library_tracks,
        metadata_reader=MetadataReader(),
    ).execute()


@router.get(
    "/alignment-runs/latest",
    response_model=LibraryAlignmentRunRead | None,
    responses=ERROR_RESPONSES,
)
def latest_alignment_run(
    libraries: LibraryRepositoryDependency,
    alignment_runs: LibraryAlignmentRunRepositoryDependency,
) -> LibraryAlignmentRunRead | None:
    return GetLatestLibraryAlignmentRun(libraries, alignment_runs).execute()
