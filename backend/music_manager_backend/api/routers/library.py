from typing import Annotated, Any

from fastapi import APIRouter, Depends

from music_manager_backend.api.dependencies import (
    get_library_alignment_run_repository,
    get_library_metadata_repository,
    get_library_repository,
    get_library_track_repository,
    get_song_library_link_repository,
    guard_library_operation,
)
from music_manager_backend.application.dtos import (
    ApiErrorRead,
    LibraryAlignmentRunRead,
    LibraryConfigure,
    LibraryMetadataAssetRead,
    LibraryMetadataImportRunRead,
    LibraryMetadataIndexEntryRead,
    LibraryRead,
    LibraryTrackRead,
)
from music_manager_backend.application.use_cases.align_library import GetLatestLibraryAlignmentRun
from music_manager_backend.application.use_cases.configure_library import ConfigureLibrary
from music_manager_backend.application.use_cases.get_library import GetLibrary
from music_manager_backend.application.use_cases.import_library_metadata import (
    GetLatestLibraryMetadataImportRun,
)
from music_manager_backend.application.use_cases.list_library_inventory import (
    ListLibraryMetadataAssets,
    ListLibraryMetadataIndexEntries,
    ListLibraryTracks,
)
from music_manager_backend.application.use_cases.scan_library import ScanLibrary
from music_manager_backend.infrastructure.audio import MetadataReader
from music_manager_backend.ports.repositories import (
    LibraryAlignmentRunRepository,
    LibraryMetadataRepository,
    LibraryRepository,
    LibraryTrackRepository,
    SongLibraryLinkRepository,
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
LibraryMetadataRepositoryDependency = Annotated[
    LibraryMetadataRepository,
    Depends(get_library_metadata_repository),
]
SongLibraryLinkRepositoryDependency = Annotated[
    SongLibraryLinkRepository,
    Depends(get_song_library_link_repository),
]


@router.get("", response_model=LibraryRead, responses=ERROR_RESPONSES)
def get_library(
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> LibraryRead:
    return GetLibrary(libraries, library_tracks, metadata_repository).execute()


@router.put("", response_model=LibraryRead, responses=ERROR_RESPONSES)
def configure_library(
    data: LibraryConfigure,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> LibraryRead:
    return ConfigureLibrary(libraries, library_tracks, metadata_repository).execute(data)


@router.post(
    "/scan",
    response_model=LibraryRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_library_operation("scan_library"))],
)
def scan_library(
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> LibraryRead:
    return ScanLibrary(
        libraries=libraries,
        library_tracks=library_tracks,
        metadata_reader=MetadataReader(),
        library_metadata=metadata_repository,
    ).execute()


@router.get("/tracks", response_model=list[LibraryTrackRead], responses=ERROR_RESPONSES)
def list_library_tracks(
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    song_library_links: SongLibraryLinkRepositoryDependency,
) -> list[LibraryTrackRead]:
    return ListLibraryTracks(libraries, library_tracks, song_library_links).execute()


@router.get(
    "/metadata/assets",
    response_model=list[LibraryMetadataAssetRead],
    responses=ERROR_RESPONSES,
)
def list_library_metadata_assets(
    libraries: LibraryRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> list[LibraryMetadataAssetRead]:
    return ListLibraryMetadataAssets(libraries, metadata_repository).execute()


@router.get(
    "/metadata/index-entries",
    response_model=list[LibraryMetadataIndexEntryRead],
    responses=ERROR_RESPONSES,
)
def list_library_metadata_index_entries(
    libraries: LibraryRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> list[LibraryMetadataIndexEntryRead]:
    return ListLibraryMetadataIndexEntries(libraries, metadata_repository).execute()


@router.get(
    "/alignment-runs/latest",
    response_model=LibraryAlignmentRunRead | None,
    responses=ERROR_RESPONSES,
)
def latest_alignment_run(
    libraries: LibraryRepositoryDependency,
    alignment_runs: LibraryAlignmentRunRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> LibraryAlignmentRunRead | None:
    return GetLatestLibraryAlignmentRun(libraries, alignment_runs, metadata_repository).execute()


@router.get(
    "/metadata/import-runs/latest",
    response_model=LibraryMetadataImportRunRead | None,
    responses=ERROR_RESPONSES,
)
def latest_metadata_import_run(
    libraries: LibraryRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> LibraryMetadataImportRunRead | None:
    return GetLatestLibraryMetadataImportRun(libraries, metadata_repository).execute()
