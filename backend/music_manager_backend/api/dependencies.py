from collections.abc import Callable, Generator
from typing import Annotated, cast

from fastapi import Depends, Request

from music_manager_backend.api.container import AppContainer, SqliteRepositoryBundle
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ExportApplyRunRepository,
    ExportPlanRepository,
    LibraryAlignmentRunRepository,
    LibraryRepository,
    LibraryTrackRepository,
    MatchLinkRepository,
    PlaylistRepository,
    RemotePlaylistRepository,
    ScanRunRepository,
    SongRepository,
    SourceDiscoveryRepository,
    SyncSnapshotRepository,
)
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter
from music_manager_backend.ports.soundcloud_discovery import SoundCloudTrackDiscoveryProvider


def get_container(request: Request) -> AppContainer:
    return cast(AppContainer, request.app.state.container)


def get_repository_bundle(
    request: Request,
) -> Generator[SqliteRepositoryBundle, None, None]:
    bundle = get_container(request).repository_bundle()
    try:
        yield bundle
    finally:
        bundle.close()


RepositoryBundleDependency = Annotated[
    SqliteRepositoryBundle,
    Depends(get_repository_bundle),
]


def get_environment_repository(bundle: RepositoryBundleDependency) -> EnvironmentRepository:
    return bundle.environment_repository


def get_audio_file_repository(bundle: RepositoryBundleDependency) -> AudioFileRepository:
    return bundle.audio_file_repository


def get_export_plan_repository(bundle: RepositoryBundleDependency) -> ExportPlanRepository:
    return bundle.export_plan_repository


def get_export_apply_run_repository(
    bundle: RepositoryBundleDependency,
) -> ExportApplyRunRepository:
    return bundle.export_apply_run_repository


def get_library_repository(bundle: RepositoryBundleDependency) -> LibraryRepository:
    return bundle.library_repository


def get_library_alignment_run_repository(
    bundle: RepositoryBundleDependency,
) -> LibraryAlignmentRunRepository:
    return bundle.library_alignment_run_repository


def get_library_track_repository(bundle: RepositoryBundleDependency) -> LibraryTrackRepository:
    return bundle.library_track_repository


def get_scan_run_repository(bundle: RepositoryBundleDependency) -> ScanRunRepository:
    return bundle.scan_run_repository


def get_match_link_repository(bundle: RepositoryBundleDependency) -> MatchLinkRepository:
    return bundle.match_link_repository


def get_remote_playlist_repository(
    bundle: RepositoryBundleDependency,
) -> RemotePlaylistRepository:
    return bundle.remote_playlist_repository


def get_playlist_repository(bundle: RepositoryBundleDependency) -> PlaylistRepository:
    return bundle.playlist_repository


def get_song_repository(bundle: RepositoryBundleDependency) -> SongRepository:
    return bundle.song_repository


def get_source_discovery_repository(
    bundle: RepositoryBundleDependency,
) -> SourceDiscoveryRepository:
    return bundle.source_discovery_repository


def get_sync_snapshot_repository(bundle: RepositoryBundleDependency) -> SyncSnapshotRepository:
    return bundle.sync_snapshot_repository


def get_soundcloud_playlist_importer(request: Request) -> SoundCloudPlaylistImporter:
    return get_container(request).soundcloud_playlist_importer


def get_soundcloud_track_discovery_provider(
    request: Request,
) -> SoundCloudTrackDiscoveryProvider:
    return get_container(request).soundcloud_track_discovery_provider


def guard_environment_operation(
    operation_name: str,
) -> Callable[[str, Request], Generator[None, None, None]]:
    def _guard(environment_id: str, request: Request) -> Generator[None, None, None]:
        with get_container(request).operation_coordinator.guard(
            environment_id=environment_id,
            operation_name=operation_name,
        ):
            yield

    return _guard


def guard_library_operation(
    operation_name: str,
) -> Callable[[Request], Generator[None, None, None]]:
    def _guard(request: Request) -> Generator[None, None, None]:
        with get_container(request).operation_coordinator.guard(
            environment_id="__library__",
            operation_name=operation_name,
        ):
            yield

    return _guard
