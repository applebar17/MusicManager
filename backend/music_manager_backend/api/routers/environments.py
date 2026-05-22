from typing import Annotated

from fastapi import APIRouter, Depends, Query

from music_manager_backend.api.dependencies import (
    get_audio_file_repository,
    get_environment_repository,
    get_playlist_repository,
    get_remote_playlist_repository,
    get_scan_run_repository,
    get_song_repository,
    get_soundcloud_playlist_importer,
    get_sync_snapshot_repository,
)
from music_manager_backend.application.dtos import (
    AudioFileRead,
    EnvironmentCreate,
    EnvironmentUpdate,
    SoundCloudPlaylistImportRequest,
    SoundCloudPlaylistImportResult,
)
from music_manager_backend.application.use_cases.archive_environment import ArchiveEnvironment
from music_manager_backend.application.use_cases.create_environment import CreateEnvironment
from music_manager_backend.application.use_cases.import_soundcloud_playlist import (
    ImportSoundCloudPlaylist,
)
from music_manager_backend.application.use_cases.list_audio_files import ListAudioFiles
from music_manager_backend.application.use_cases.list_unmanaged_files import ListUnmanagedFiles
from music_manager_backend.application.use_cases.scan_environment import ScanEnvironment
from music_manager_backend.application.use_cases.update_environment import UpdateEnvironment
from music_manager_backend.domain.entities import AudioFile, MusicEnvironment
from music_manager_backend.infrastructure.audio import MetadataReader
from music_manager_backend.infrastructure.filesystem import LocalAudioScanner
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    PlaylistRepository,
    RemotePlaylistRepository,
    ScanRunRepository,
    SongRepository,
    SyncSnapshotRepository,
)
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter

router = APIRouter(prefix="/environments", tags=["environments"])
EnvironmentRepositoryDependency = Annotated[
    EnvironmentRepository,
    Depends(get_environment_repository),
]
AudioFileRepositoryDependency = Annotated[
    AudioFileRepository,
    Depends(get_audio_file_repository),
]
ScanRunRepositoryDependency = Annotated[
    ScanRunRepository,
    Depends(get_scan_run_repository),
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


@router.get("")
def list_environments(
    repository: EnvironmentRepositoryDependency,
    include_archived: bool = False,
) -> list[dict[str, str | None]]:
    return [
        _environment_response(item)
        for item in repository.list(include_archived=include_archived)
    ]


@router.post("")
def create_environment(
    data: EnvironmentCreate,
    repository: EnvironmentRepositoryDependency,
) -> dict[str, str | None]:
    environment = CreateEnvironment(repository).execute(data)
    return _environment_response(environment)


@router.patch("/{environment_id}")
def update_environment(
    environment_id: str,
    data: EnvironmentUpdate,
    repository: EnvironmentRepositoryDependency,
) -> dict[str, str | None]:
    environment = UpdateEnvironment(repository).execute(environment_id, data)
    return _environment_response(environment)


@router.post("/{environment_id}/archive")
def archive_environment(
    environment_id: str,
    repository: EnvironmentRepositoryDependency,
) -> dict[str, str | None]:
    environment = ArchiveEnvironment(repository).execute(environment_id)
    return _environment_response(environment)


@router.post("/{environment_id}/scan")
def scan_environment(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    scan_runs: ScanRunRepositoryDependency,
) -> dict[str, int | str]:
    summary = ScanEnvironment(
        environments=environments,
        audio_files=audio_files,
        scan_runs=scan_runs,
        scanner_factory=LocalAudioScanner,
        metadata_reader=MetadataReader(),
    ).execute(environment_id)
    return {
        "scan_run_id": summary.scan_run_id,
        "environment_id": summary.environment_id,
        "added": summary.added,
        "changed": summary.changed,
        "removed": summary.removed,
        "moved": summary.moved,
        "unchanged": summary.unchanged,
        "total_active": summary.total_active,
    }


@router.post("/{environment_id}/soundcloud/playlists")
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


@router.get("/{environment_id}/audio-files")
def list_audio_files(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
    status: str = Query(default="active"),
) -> list[AudioFileRead]:
    files = ListAudioFiles(environments, audio_files).execute(environment_id, status=status)
    return [_audio_file_response(item) for item in files]


@router.get("/{environment_id}/unmanaged-files")
def list_unmanaged_files(
    environment_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
) -> list[AudioFileRead]:
    files = ListUnmanagedFiles(environments, audio_files).execute(environment_id)
    return [_audio_file_response(item) for item in files]


def _environment_response(environment: MusicEnvironment) -> dict[str, str | None]:
    return {
        "id": environment.id,
        "name": environment.name,
        "root_path": str(environment.root_path),
        "deprecated_folder_name": environment.deprecated_folder_name,
        "archived_at": environment.archived_at,
    }


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
