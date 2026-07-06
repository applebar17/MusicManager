import logging
import sys
from contextlib import AbstractContextManager
from dataclasses import replace
from threading import Thread
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from music_manager_backend.api.dependencies import (
    get_audio_file_repository,
    get_environment_repository,
    get_export_apply_run_repository,
    get_export_plan_repository,
    get_library_alignment_run_repository,
    get_library_metadata_repository,
    get_library_repository,
    get_library_track_repository,
    get_match_link_repository,
    get_playlist_repository,
    get_remote_playlist_repository,
    get_scan_run_repository,
    get_song_repository,
    get_song_library_link_repository,
    get_soundcloud_playlist_importer,
    get_soundcloud_track_discovery_provider,
    get_source_discovery_repository,
    get_sync_snapshot_repository,
    get_container,
    guard_environment_operation,
    guard_library_operation,
)
from music_manager_backend.application.dtos import (
    ApiErrorRead,
    AudioFileRead,
    DownloadMatchRunResultRead,
    EnvironmentCreate,
    EnvironmentOverviewRead,
    EnvironmentRead,
    EnvironmentUpdate,
    ExportApplyRunRead,
    ExportPlanCreate,
    ExportPlanRead,
    ExportPlanUpdate,
    LibraryAlignmentRunRead,
    LibraryMatchingRunSummary,
    LibraryMatchReviewRow,
    LibraryMetadataImportRunRead,
    LibraryTrackCandidateRead,
    ManualLibraryMappingCreate,
    ManualMappingCreate,
    MatchCandidateRead,
    MatchingRunSummary,
    MatchReviewRow,
    PlaylistDetailRead,
    PlaylistLocalItemCreate,
    PlaylistSummaryRead,
    ScanSummaryRead,
    SoundCloudPlaylistImportRequest,
    SoundCloudPlaylistImportResult,
    SoundCloudPlaylistSyncAllResult,
    SoundCloudSourceSyncResultRead,
    SoundCloudTrackDiscoveryRead,
    UsbAudioFileBatchQuarantineRequest,
    UsbAudioFileBatchQuarantineResult,
    UsbAudioFileMappingCreate,
    UsbFileRead,
    UsbSongCandidateRead,
    environment_read,
    export_apply_run_read,
    export_plan_read,
)
from music_manager_backend.application.use_cases.apply_export_plan import ApplyExportPlan
from music_manager_backend.application.use_cases.archive_environment import ArchiveEnvironment
from music_manager_backend.application.use_cases.align_library import AlignLibraryFromEnvironment
from music_manager_backend.application.use_cases.create_environment import CreateEnvironment
from music_manager_backend.application.use_cases.create_manual_mapping import CreateManualMapping
from music_manager_backend.application.use_cases.discover_soundcloud_track import (
    DiscoverSoundCloudTrack,
)
from music_manager_backend.application.use_cases.get_environment_overview import (
    GetEnvironmentOverview,
)
from music_manager_backend.application.use_cases.get_export_apply_run import GetExportApplyRun
from music_manager_backend.application.use_cases.get_playlist_detail import GetPlaylistDetail
from music_manager_backend.application.use_cases.import_soundcloud_playlist import (
    ImportSoundCloudPlaylist,
)
from music_manager_backend.application.use_cases.import_library_metadata import (
    ImportLibraryMetadataFromEnvironment,
)
from music_manager_backend.application.use_cases.list_audio_files import ListAudioFiles
from music_manager_backend.application.use_cases.list_environment_playlists import (
    ListEnvironmentPlaylists,
)
from music_manager_backend.application.use_cases.list_export_plan import ListExportPlan
from music_manager_backend.application.use_cases.list_manual_audio_file_candidates import (
    ListManualAudioFileCandidates,
)
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.application.use_cases.library_matching import (
    CreateManualLibraryMapping,
    ListLibraryMatchReview,
    ListManualLibraryTrackCandidates,
    RunLibraryMatching,
)
from music_manager_backend.application.use_cases.list_unmanaged_files import ListUnmanagedFiles
from music_manager_backend.application.use_cases.match_downloads import MatchDownloads
from music_manager_backend.application.use_cases.manage_playlist_local_items import (
    AddPlaylistLocalItem,
    RemovePlaylistLocalItem,
)
from music_manager_backend.application.use_cases.plan_export import PlanExport
from music_manager_backend.application.use_cases.run_matching import RunMatching
from music_manager_backend.application.use_cases.scan_environment import ScanEnvironment
from music_manager_backend.application.use_cases.sync_all_soundcloud_playlists import (
    SyncAllSoundCloudPlaylists,
)
from music_manager_backend.application.use_cases.sync_soundcloud_playlist import (
    SyncSoundCloudPlaylist,
)
from music_manager_backend.application.use_cases.sync_soundcloud_sources import (
    SyncMissingSoundCloudSources,
)
from music_manager_backend.application.use_cases.update_environment import UpdateEnvironment
from music_manager_backend.application.use_cases.update_export_plan import UpdateExportPlan
from music_manager_backend.application.use_cases.usb_files import (
    CreateUsbAudioFileMapping,
    ListUsbFiles,
    ListUsbMatchCandidates,
    QuarantineUsbAudioFile,
    QuarantineUsbAudioFiles,
)
from music_manager_backend.api.container import AppContainer
from music_manager_backend.domain.entities import AudioFile, ExportApplyRunStatus
from music_manager_backend.infrastructure.audio import MetadataReader
from music_manager_backend.infrastructure.filesystem import LocalAudioScanner
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ExportApplyRunRepository,
    ExportPlanRepository,
    LibraryAlignmentRunRepository,
    LibraryMetadataRepository,
    LibraryRepository,
    LibraryTrackRepository,
    MatchLinkRepository,
    PlaylistRepository,
    RemotePlaylistRepository,
    ScanRunRepository,
    SongRepository,
    SongLibraryLinkRepository,
    SourceDiscoveryRepository,
    SyncSnapshotRepository,
)
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter
from music_manager_backend.ports.soundcloud_discovery import SoundCloudTrackDiscoveryProvider
from music_manager_backend.shared.time import utc_now_iso

logger = logging.getLogger(__name__)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorRead},
    404: {"model": ApiErrorRead},
    409: {"model": ApiErrorRead},
    422: {"model": ApiErrorRead},
    503: {"model": ApiErrorRead},
}

router = APIRouter(prefix="/environments", tags=["environments"])
EnvironmentRepositoryDependency = Annotated[
    EnvironmentRepository,
    Depends(get_environment_repository),
]
AudioFileRepositoryDependency = Annotated[
    AudioFileRepository,
    Depends(get_audio_file_repository),
]
ExportPlanRepositoryDependency = Annotated[
    ExportPlanRepository,
    Depends(get_export_plan_repository),
]
ExportApplyRunRepositoryDependency = Annotated[
    ExportApplyRunRepository,
    Depends(get_export_apply_run_repository),
]
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
ScanRunRepositoryDependency = Annotated[
    ScanRunRepository,
    Depends(get_scan_run_repository),
]
MatchLinkRepositoryDependency = Annotated[
    MatchLinkRepository,
    Depends(get_match_link_repository),
]
RemotePlaylistRepositoryDependency = Annotated[
    RemotePlaylistRepository,
    Depends(get_remote_playlist_repository),
]
PlaylistRepositoryDependency = Annotated[
    PlaylistRepository,
    Depends(get_playlist_repository),
]
SongRepositoryDependency = Annotated[
    SongRepository,
    Depends(get_song_repository),
]
SongLibraryLinkRepositoryDependency = Annotated[
    SongLibraryLinkRepository,
    Depends(get_song_library_link_repository),
]
SourceDiscoveryRepositoryDependency = Annotated[
    SourceDiscoveryRepository,
    Depends(get_source_discovery_repository),
]
SyncSnapshotRepositoryDependency = Annotated[
    SyncSnapshotRepository,
    Depends(get_sync_snapshot_repository),
]
SoundCloudPlaylistImporterDependency = Annotated[
    SoundCloudPlaylistImporter,
    Depends(get_soundcloud_playlist_importer),
]
SoundCloudTrackDiscoveryProviderDependency = Annotated[
    SoundCloudTrackDiscoveryProvider,
    Depends(get_soundcloud_track_discovery_provider),
]


@router.get("", response_model=list[EnvironmentRead], responses=ERROR_RESPONSES)
def list_environments(
    repository: EnvironmentRepositoryDependency,
    include_archived: bool = False,
) -> list[EnvironmentRead]:
    return [
        environment_read(item)
        for item in repository.list(include_archived=include_archived)
    ]


@router.post("", response_model=EnvironmentRead, responses=ERROR_RESPONSES)
def create_environment(
    data: EnvironmentCreate,
    repository: EnvironmentRepositoryDependency,
) -> EnvironmentRead:
    environment = CreateEnvironment(repository).execute(data)
    return environment_read(environment)


@router.patch(
    "/{environment_id}",
    response_model=EnvironmentRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("update_environment"))],
)
def update_environment(
    environment_id: str,
    data: EnvironmentUpdate,
    repository: EnvironmentRepositoryDependency,
) -> EnvironmentRead:
    environment = UpdateEnvironment(repository).execute(environment_id, data)
    return environment_read(environment)


@router.post(
    "/{environment_id}/archive",
    response_model=EnvironmentRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("archive_environment"))],
)
def archive_environment(
    environment_id: str,
    repository: EnvironmentRepositoryDependency,
) -> EnvironmentRead:
    environment = ArchiveEnvironment(repository).execute(environment_id)
    return environment_read(environment)


@router.post(
    "/{environment_id}/scan",
    response_model=ScanSummaryRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("scan_environment"))],
)
def scan_environment(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    scan_runs: ScanRunRepositoryDependency,
) -> ScanSummaryRead:
    summary = ScanEnvironment(
        environments=environments,
        audio_files=audio_files,
        scan_runs=scan_runs,
        scanner_factory=LocalAudioScanner,
        metadata_reader=MetadataReader(),
    ).execute(environment_id)
    return ScanSummaryRead(
        scan_run_id=summary.scan_run_id,
        environment_id=summary.environment_id,
        added=summary.added,
        changed=summary.changed,
        removed=summary.removed,
        moved=summary.moved,
        unchanged=summary.unchanged,
        total_active=summary.total_active,
    )


@router.post(
    "/{environment_id}/soundcloud/playlists",
    response_model=SoundCloudPlaylistImportResult,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("import_soundcloud_playlist"))],
)
def import_soundcloud_playlist(
    environment_id: str,
    data: SoundCloudPlaylistImportRequest,
    environments: EnvironmentRepositoryDependency,
    remote_playlists: RemotePlaylistRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    sync_snapshots: SyncSnapshotRepositoryDependency,
    importer: SoundCloudPlaylistImporterDependency,
) -> SoundCloudPlaylistImportResult:
    return ImportSoundCloudPlaylist(
        environments=environments,
        remote_playlists=remote_playlists,
        playlists=playlists,
        songs=songs,
        sync_snapshots=sync_snapshots,
        importer=importer,
    ).execute(environment_id, data.url)


@router.post(
    "/{environment_id}/soundcloud/playlists/sync-all",
    response_model=SoundCloudPlaylistSyncAllResult,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("sync_all_soundcloud_playlists"))],
)
def sync_all_soundcloud_playlists(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    remote_playlists: RemotePlaylistRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    sync_snapshots: SyncSnapshotRepositoryDependency,
    importer: SoundCloudPlaylistImporterDependency,
) -> SoundCloudPlaylistSyncAllResult:
    return SyncAllSoundCloudPlaylists(
        environments=environments,
        remote_playlists=remote_playlists,
        playlists=playlists,
        songs=songs,
        sync_snapshots=sync_snapshots,
        importer=importer,
    ).execute(environment_id)


@router.post(
    "/{environment_id}/soundcloud/playlists/{playlist_id}/sync",
    response_model=SoundCloudPlaylistImportResult,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("sync_soundcloud_playlist"))],
)
def sync_soundcloud_playlist(
    environment_id: str,
    playlist_id: str,
    environments: EnvironmentRepositoryDependency,
    remote_playlists: RemotePlaylistRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    sync_snapshots: SyncSnapshotRepositoryDependency,
    importer: SoundCloudPlaylistImporterDependency,
) -> SoundCloudPlaylistImportResult:
    return SyncSoundCloudPlaylist(
        environments=environments,
        remote_playlists=remote_playlists,
        playlists=playlists,
        songs=songs,
        sync_snapshots=sync_snapshots,
        importer=importer,
    ).execute(environment_id, playlist_id)


@router.post(
    "/{environment_id}/matching/run",
    response_model=MatchingRunSummary,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("run_matching"))],
)
def run_matching(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
) -> MatchingRunSummary:
    return RunMatching(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id)


@router.post(
    "/{environment_id}/library/matching/run",
    response_model=LibraryMatchingRunSummary,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("run_library_matching"))],
)
def run_library_matching(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    song_library_links: SongLibraryLinkRepositoryDependency,
) -> LibraryMatchingRunSummary:
    return RunLibraryMatching(
        environments=environments,
        playlists=playlists,
        songs=songs,
        libraries=libraries,
        library_tracks=library_tracks,
        song_library_links=song_library_links,
    ).execute(environment_id)


@router.post(
    "/{environment_id}/matching/downloads/run",
    response_model=DownloadMatchRunResultRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("match_downloads"))],
)
def match_downloads(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    scan_runs: ScanRunRepositoryDependency,
) -> DownloadMatchRunResultRead:
    return MatchDownloads(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        scan_runs=scan_runs,
        scanner_factory=LocalAudioScanner,
        metadata_reader=MetadataReader(),
    ).execute(environment_id)


@router.get(
    "/{environment_id}/matching/review",
    response_model=list[MatchReviewRow],
    responses=ERROR_RESPONSES,
)
def list_match_review(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    source_discoveries: SourceDiscoveryRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    song_library_links: SongLibraryLinkRepositoryDependency,
) -> list[MatchReviewRow]:
    return ListMatchReview(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        source_discoveries=source_discoveries,
        libraries=libraries,
        library_tracks=library_tracks,
        song_library_links=song_library_links,
    ).execute(environment_id)


@router.get(
    "/{environment_id}/library/matching/review",
    response_model=list[LibraryMatchReviewRow],
    responses=ERROR_RESPONSES,
)
def list_library_match_review(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    song_library_links: SongLibraryLinkRepositoryDependency,
) -> list[LibraryMatchReviewRow]:
    return ListLibraryMatchReview(
        environments=environments,
        playlists=playlists,
        songs=songs,
        libraries=libraries,
        library_tracks=library_tracks,
        song_library_links=song_library_links,
    ).execute(environment_id)


@router.get(
    "/{environment_id}/matching/manual-file-candidates",
    response_model=list[MatchCandidateRead],
    responses=ERROR_RESPONSES,
)
def list_manual_audio_file_candidates(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    song_id: str = Query(...),
    q: str = Query(default=""),
) -> list[MatchCandidateRead]:
    return ListManualAudioFileCandidates(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id, song_id=song_id, query=q)


@router.get(
    "/{environment_id}/library/matching/manual-track-candidates",
    response_model=list[LibraryTrackCandidateRead],
    responses=ERROR_RESPONSES,
)
def list_manual_library_track_candidates(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    song_library_links: SongLibraryLinkRepositoryDependency,
    song_id: str = Query(...),
    q: str = Query(default=""),
) -> list[LibraryTrackCandidateRead]:
    return ListManualLibraryTrackCandidates(
        environments=environments,
        playlists=playlists,
        songs=songs,
        libraries=libraries,
        library_tracks=library_tracks,
        song_library_links=song_library_links,
    ).execute(environment_id, song_id=song_id, query=q)


@router.post(
    "/{environment_id}/matching/manual-mappings",
    response_model=MatchReviewRow,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("create_manual_mapping"))],
)
def create_manual_mapping(
    environment_id: str,
    data: ManualMappingCreate,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
) -> MatchReviewRow:
    return CreateManualMapping(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id, data.song_id, data.audio_file_id)


@router.post(
    "/{environment_id}/library/matching/manual-mappings",
    response_model=LibraryMatchReviewRow,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("create_manual_library_mapping"))],
)
def create_manual_library_mapping(
    environment_id: str,
    data: ManualLibraryMappingCreate,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    song_library_links: SongLibraryLinkRepositoryDependency,
) -> LibraryMatchReviewRow:
    return CreateManualLibraryMapping(
        environments=environments,
        playlists=playlists,
        songs=songs,
        libraries=libraries,
        library_tracks=library_tracks,
        song_library_links=song_library_links,
    ).execute(environment_id, data.song_id, data.library_track_id)


@router.get(
    "/{environment_id}/songs/{song_id}/soundcloud-discovery",
    response_model=SoundCloudTrackDiscoveryRead,
    responses=ERROR_RESPONSES,
)
def discover_soundcloud_track(
    environment_id: str,
    song_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    source_discoveries: SourceDiscoveryRepositoryDependency,
    discovery_provider: SoundCloudTrackDiscoveryProviderDependency,
) -> SoundCloudTrackDiscoveryRead:
    return DiscoverSoundCloudTrack(
        environments=environments,
        playlists=playlists,
        songs=songs,
        source_discoveries=source_discoveries,
        discovery_provider=discovery_provider,
    ).execute(environment_id, song_id)


@router.post(
    "/{environment_id}/soundcloud-discovery/sync-missing",
    response_model=SoundCloudSourceSyncResultRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("sync_soundcloud_sources"))],
)
def sync_missing_soundcloud_sources(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    source_discoveries: SourceDiscoveryRepositoryDependency,
    discovery_provider: SoundCloudTrackDiscoveryProviderDependency,
) -> SoundCloudSourceSyncResultRead:
    return SyncMissingSoundCloudSources(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        source_discoveries=source_discoveries,
        discovery_provider=discovery_provider,
    ).execute(environment_id)


@router.get(
    "/{environment_id}/usb/files",
    response_model=list[UsbFileRead],
    responses=ERROR_RESPONSES,
)
def list_usb_files(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
) -> list[UsbFileRead]:
    return ListUsbFiles(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id)


@router.get(
    "/{environment_id}/usb/match-candidates",
    response_model=list[UsbSongCandidateRead],
    responses=ERROR_RESPONSES,
)
def list_usb_match_candidates(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    audio_file_id: str = Query(...),
    q: str = Query(default=""),
) -> list[UsbSongCandidateRead]:
    return ListUsbMatchCandidates(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id, audio_file_id=audio_file_id, query=q)


@router.post(
    "/{environment_id}/usb/audio-files/{audio_file_id}/mapping",
    response_model=UsbFileRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("map_usb_audio_file"))],
)
def map_usb_audio_file(
    environment_id: str,
    audio_file_id: str,
    data: UsbAudioFileMappingCreate,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
) -> UsbFileRead:
    return CreateUsbAudioFileMapping(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id, audio_file_id, data)


@router.post(
    "/{environment_id}/usb/audio-files/quarantine",
    response_model=UsbAudioFileBatchQuarantineResult,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("quarantine_usb_audio_files"))],
)
def quarantine_usb_audio_files(
    environment_id: str,
    data: UsbAudioFileBatchQuarantineRequest,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
) -> UsbAudioFileBatchQuarantineResult:
    return QuarantineUsbAudioFiles(
        environments=environments,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(
        environment_id,
        audio_file_ids=data.audio_file_ids,
        confirmation=data.confirmation,
    )


@router.post(
    "/{environment_id}/usb/audio-files/{audio_file_id}/quarantine",
    response_model=UsbFileRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("quarantine_usb_audio_file"))],
)
def quarantine_usb_audio_file(
    environment_id: str,
    audio_file_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
) -> UsbFileRead:
    return QuarantineUsbAudioFile(
        environments=environments,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id, audio_file_id)


@router.post(
    "/{environment_id}/library/align",
    response_model=LibraryAlignmentRunRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_library_operation("align_library"))],
)
def align_library_from_environment(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    alignment_runs: LibraryAlignmentRunRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> LibraryAlignmentRunRead:
    return AlignLibraryFromEnvironment(
        environments=environments,
        libraries=libraries,
        library_tracks=library_tracks,
        alignment_runs=alignment_runs,
        scanner_factory=LocalAudioScanner,
        metadata_reader=MetadataReader(),
        metadata_repository=metadata_repository,
    ).execute(environment_id)


@router.post(
    "/{environment_id}/library/metadata/import",
    response_model=LibraryMetadataImportRunRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_library_operation("import_library_metadata"))],
)
def import_library_metadata_from_environment(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    alignment_runs: LibraryAlignmentRunRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
) -> LibraryMetadataImportRunRead:
    return ImportLibraryMetadataFromEnvironment(
        environments=environments,
        libraries=libraries,
        library_tracks=library_tracks,
        alignment_runs=alignment_runs,
        metadata_repository=metadata_repository,
    ).execute(environment_id)


@router.get(
    "/{environment_id}/overview",
    response_model=EnvironmentOverviewRead,
    responses=ERROR_RESPONSES,
)
def get_environment_overview(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
) -> EnvironmentOverviewRead:
    return GetEnvironmentOverview(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id)


@router.get(
    "/{environment_id}/playlists",
    response_model=list[PlaylistSummaryRead],
    responses=ERROR_RESPONSES,
)
def list_environment_playlists(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
) -> list[PlaylistSummaryRead]:
    return ListEnvironmentPlaylists(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id)


@router.get(
    "/{environment_id}/playlists/{playlist_id}",
    response_model=PlaylistDetailRead,
    responses=ERROR_RESPONSES,
)
def get_playlist_detail(
    environment_id: str,
    playlist_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    source_discoveries: SourceDiscoveryRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    song_library_links: SongLibraryLinkRepositoryDependency,
) -> PlaylistDetailRead:
    return GetPlaylistDetail(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        source_discoveries=source_discoveries,
        libraries=libraries,
        library_tracks=library_tracks,
        song_library_links=song_library_links,
    ).execute(environment_id, playlist_id)


@router.post(
    "/{environment_id}/playlists/{playlist_id}/local-items",
    response_model=PlaylistDetailRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("add_playlist_local_item"))],
)
def add_playlist_local_item(
    environment_id: str,
    playlist_id: str,
    data: PlaylistLocalItemCreate,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    source_discoveries: SourceDiscoveryRepositoryDependency,
) -> PlaylistDetailRead:
    return AddPlaylistLocalItem(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        source_discoveries=source_discoveries,
    ).execute(environment_id, playlist_id, data.audio_file_id)


@router.delete(
    "/{environment_id}/playlists/{playlist_id}/local-items/{song_id}",
    response_model=PlaylistDetailRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("remove_playlist_local_item"))],
)
def remove_playlist_local_item(
    environment_id: str,
    playlist_id: str,
    song_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    source_discoveries: SourceDiscoveryRepositoryDependency,
) -> PlaylistDetailRead:
    return RemovePlaylistLocalItem(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        source_discoveries=source_discoveries,
    ).execute(environment_id, playlist_id, song_id)


@router.post(
    "/{environment_id}/export-plans",
    response_model=ExportPlanRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("create_export_plan"))],
)
def create_export_plan(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    playlists: PlaylistRepositoryDependency,
    songs: SongRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    match_links: MatchLinkRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    song_library_links: SongLibraryLinkRepositoryDependency,
    metadata_repository: LibraryMetadataRepositoryDependency,
    export_plans: ExportPlanRepositoryDependency,
    data: ExportPlanCreate | None = None,
) -> ExportPlanRead:
    plan = PlanExport(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        libraries=libraries,
        library_tracks=library_tracks,
        song_library_links=song_library_links,
        library_metadata=metadata_repository,
        export_plans=export_plans,
        metadata_reader=MetadataReader(),
    ).execute(environment_id, data.playlist_ids if data is not None else None)
    return export_plan_read(plan)


@router.get(
    "/{environment_id}/export-plans/{export_plan_id}",
    response_model=ExportPlanRead,
    responses=ERROR_RESPONSES,
)
def get_export_plan(
    environment_id: str,
    export_plan_id: str,
    environments: EnvironmentRepositoryDependency,
    export_plans: ExportPlanRepositoryDependency,
) -> ExportPlanRead:
    plan = ListExportPlan(
        environments=environments,
        export_plans=export_plans,
    ).execute(environment_id, export_plan_id)
    return export_plan_read(plan)


@router.patch(
    "/{environment_id}/export-plans/{export_plan_id}",
    response_model=ExportPlanRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("update_export_plan"))],
)
def update_export_plan(
    environment_id: str,
    export_plan_id: str,
    data: ExportPlanUpdate,
    environments: EnvironmentRepositoryDependency,
    export_plans: ExportPlanRepositoryDependency,
) -> ExportPlanRead:
    plan = UpdateExportPlan(
        environments=environments,
        export_plans=export_plans,
    ).execute(environment_id, export_plan_id, data)
    return export_plan_read(plan)


@router.post(
    "/{environment_id}/export-plans/{export_plan_id}/apply",
    response_model=ExportApplyRunRead,
    responses=ERROR_RESPONSES,
)
def apply_export_plan(
    environment_id: str,
    export_plan_id: str,
    request: Request,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    libraries: LibraryRepositoryDependency,
    library_tracks: LibraryTrackRepositoryDependency,
    export_plans: ExportPlanRepositoryDependency,
    apply_runs: ExportApplyRunRepositoryDependency,
) -> ExportApplyRunRead:
    container = get_container(request)
    operation_guard = container.operation_coordinator.guard(
        environment_id=environment_id,
        operation_name="apply_export_plan",
    )
    operation_guard.__enter__()
    try:
        apply_run = ApplyExportPlan(
            environments=environments,
            audio_files=audio_files,
            libraries=libraries,
            library_tracks=library_tracks,
            export_plans=export_plans,
            apply_runs=apply_runs,
        ).start(environment_id, export_plan_id)
        Thread(
            target=_run_export_apply_worker,
            args=(container, apply_run.id, operation_guard),
            daemon=True,
        ).start()
    except BaseException:
        operation_guard.__exit__(*sys.exc_info())
        raise
    return export_apply_run_read(apply_run)


@router.get(
    "/{environment_id}/export-apply-runs/{apply_run_id}",
    response_model=ExportApplyRunRead,
    responses=ERROR_RESPONSES,
)
def get_export_apply_run(
    environment_id: str,
    apply_run_id: str,
    environments: EnvironmentRepositoryDependency,
    apply_runs: ExportApplyRunRepositoryDependency,
) -> ExportApplyRunRead:
    apply_run = GetExportApplyRun(
        environments=environments,
        apply_runs=apply_runs,
    ).execute(environment_id, apply_run_id)
    return export_apply_run_read(apply_run)


@router.get(
    "/{environment_id}/audio-files",
    response_model=list[AudioFileRead],
    responses=ERROR_RESPONSES,
)
def list_audio_files(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    status: str = Query(default="active"),
) -> list[AudioFileRead]:
    files = ListAudioFiles(environments, audio_files).execute(environment_id, status=status)
    return [_audio_file_response(item) for item in files]


@router.get(
    "/{environment_id}/unmanaged-files",
    response_model=list[AudioFileRead],
    responses=ERROR_RESPONSES,
)
def list_unmanaged_files(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
) -> list[AudioFileRead]:
    files = ListUnmanagedFiles(environments, audio_files).execute(environment_id)
    return [_audio_file_response(item) for item in files]


def _audio_file_response(audio_file: AudioFile) -> AudioFileRead:
    return AudioFileRead(
        id=audio_file.id,
        environment_id=audio_file.environment_id,
        path=str(audio_file.path),
        size_bytes=audio_file.size_bytes,
        modified_at=audio_file.modified_at,
        status=audio_file.status.value,
        title=audio_file.title,
        artist=audio_file.artist,
        album=audio_file.album,
        duration_seconds=audio_file.duration_seconds,
        bpm=audio_file.bpm,
        key=audio_file.key,
        comment=audio_file.comment,
    )


def _run_export_apply_worker(
    container: AppContainer,
    apply_run_id: str,
    operation_guard: AbstractContextManager[None],
) -> None:
    try:
        with container.repository_bundle() as repositories:
            ApplyExportPlan(
                environments=repositories.environment_repository,
                audio_files=repositories.audio_file_repository,
                libraries=repositories.library_repository,
                library_tracks=repositories.library_track_repository,
                export_plans=repositories.export_plan_repository,
                apply_runs=repositories.export_apply_run_repository,
            ).run(apply_run_id)
    except Exception as exc:
        logger.exception("Export apply worker failed apply_run_id=%s", apply_run_id)
        _mark_apply_run_failed(container, apply_run_id, exc)
    finally:
        operation_guard.__exit__(None, None, None)


def _mark_apply_run_failed(
    container: AppContainer,
    apply_run_id: str,
    exc: Exception,
) -> None:
    try:
        with container.repository_bundle() as repositories:
            apply_run = repositories.export_apply_run_repository.get(apply_run_id)
            if apply_run is None:
                return
            repositories.export_apply_run_repository.save(
                replace(
                    apply_run,
                    status=ExportApplyRunStatus.FAILED,
                    finished_at=utc_now_iso(),
                )
            )
    except Exception:
        logger.exception("Failed to mark export apply run failed apply_run_id=%s", apply_run_id)
