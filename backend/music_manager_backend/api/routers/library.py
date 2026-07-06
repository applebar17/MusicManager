from typing import Annotated, Any

from fastapi import APIRouter, Depends

from music_manager_backend.api.dependencies import (
    get_library_repository,
    get_library_track_repository,
)
from music_manager_backend.application.dtos import ApiErrorRead, LibraryConfigure, LibraryRead
from music_manager_backend.application.use_cases.configure_library import ConfigureLibrary
from music_manager_backend.application.use_cases.get_library import GetLibrary
from music_manager_backend.ports.repositories import LibraryRepository, LibraryTrackRepository

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorRead},
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
