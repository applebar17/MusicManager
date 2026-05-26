from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from music_manager_backend.api.dependencies import (
    get_audio_file_repository,
    get_environment_repository,
    get_export_apply_run_repository,
    get_export_plan_repository,
    get_match_link_repository,
    get_playlist_repository,
    get_remote_playlist_repository,
    get_scan_run_repository,
    get_song_repository,
    get_soundcloud_playlist_importer,
    get_sync_snapshot_repository,
    guard_environment_operation,
)
from music_manager_backend.application.dtos import (
    ApiErrorRead,
    AudioFileRead,
    EnvironmentCreate,
    EnvironmentOverviewRead,
    EnvironmentRead,
    EnvironmentUpdate,
    ExportApplyRunRead,
    ExportPlanCreate,
    ExportPlanRead,
    ManualMappingCreate,
    MatchingRunSummary,
    MatchReviewRow,
    PlaylistDetailRead,
    PlaylistSummaryRead,
    ScanSummaryRead,
    SoundCloudPlaylistImportRequest,
    SoundCloudPlaylistImportResult,
    SoundCloudPlaylistSyncAllResult,
    UsbFileRead,
    UsbSongCandidateRead,
    environment_read,
    export_apply_run_read,
    export_plan_read,
)
from music_manager_backend.application.use_cases.apply_export_plan import ApplyExportPlan
from music_manager_backend.application.use_cases.archive_environment import ArchiveEnvironment
from music_manager_backend.application.use_cases.create_environment import CreateEnvironment
from music_manager_backend.application.use_cases.create_manual_mapping import CreateManualMapping
from music_manager_backend.application.use_cases.get_environment_overview import (
    GetEnvironmentOverview,
)
from music_manager_backend.application.use_cases.get_export_apply_run import GetExportApplyRun
from music_manager_backend.application.use_cases.get_playlist_detail import GetPlaylistDetail
from music_manager_backend.application.use_cases.import_soundcloud_playlist import (
    ImportSoundCloudPlaylist,
)
from music_manager_backend.application.use_cases.list_audio_files import ListAudioFiles
from music_manager_backend.application.use_cases.list_environment_playlists import (
    ListEnvironmentPlaylists,
)
from music_manager_backend.application.use_cases.list_export_plan import ListExportPlan
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.application.use_cases.list_unmanaged_files import ListUnmanagedFiles
from music_manager_backend.application.use_cases.plan_export import PlanExport
from music_manager_backend.application.use_cases.run_matching import RunMatching
from music_manager_backend.application.use_cases.scan_environment import ScanEnvironment
from music_manager_backend.application.use_cases.sync_all_soundcloud_playlists import (
    SyncAllSoundCloudPlaylists,
)
from music_manager_backend.application.use_cases.update_environment import UpdateEnvironment
from music_manager_backend.application.use_cases.usb_files import (
    ListUsbFiles,
    ListUsbMatchCandidates,
    QuarantineUsbAudioFile,
)
from music_manager_backend.domain.entities import AudioFile
from music_manager_backend.infrastructure.audio import MetadataReader
from music_manager_backend.infrastructure.filesystem import LocalAudioScanner
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ExportApplyRunRepository,
    ExportPlanRepository,
    MatchLinkRepository,
    PlaylistRepository,
    RemotePlaylistRepository,
    ScanRunRepository,
    SongRepository,
    SyncSnapshotRepository,
)
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter

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
SyncSnapshotRepositoryDependency = Annotated[
    SyncSnapshotRepository,
    Depends(get_sync_snapshot_repository),
]
SoundCloudPlaylistImporterDependency = Annotated[
    SoundCloudPlaylistImporter,
    Depends(get_soundcloud_playlist_importer),
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
) -> list[MatchReviewRow]:
    return ListMatchReview(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id)


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
) -> PlaylistDetailRead:
    return GetPlaylistDetail(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
    ).execute(environment_id, playlist_id)


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
    export_plans: ExportPlanRepositoryDependency,
    data: ExportPlanCreate | None = None,
) -> ExportPlanRead:
    plan = PlanExport(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        export_plans=export_plans,
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


@router.post(
    "/{environment_id}/export-plans/{export_plan_id}/apply",
    response_model=ExportApplyRunRead,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(guard_environment_operation("apply_export_plan"))],
)
def apply_export_plan(
    environment_id: str,
    export_plan_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    export_plans: ExportPlanRepositoryDependency,
    apply_runs: ExportApplyRunRepositoryDependency,
) -> ExportApplyRunRead:
    apply_run = ApplyExportPlan(
        environments=environments,
        audio_files=audio_files,
        export_plans=export_plans,
        apply_runs=apply_runs,
    ).execute(environment_id, export_plan_id)
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
