from typing import cast

from fastapi import Request

from music_manager_backend.api.container import AppContainer
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


def get_container(request: Request) -> AppContainer:
    return cast(AppContainer, request.app.state.container)


def get_environment_repository(request: Request) -> EnvironmentRepository:
    return get_container(request).environment_repository


def get_audio_file_repository(request: Request) -> AudioFileRepository:
    return get_container(request).audio_file_repository


def get_scan_run_repository(request: Request) -> ScanRunRepository:
    return get_container(request).scan_run_repository


def get_remote_playlist_repository(request: Request) -> RemotePlaylistRepository:
    return get_container(request).remote_playlist_repository


def get_playlist_repository(request: Request) -> PlaylistRepository:
    return get_container(request).playlist_repository


def get_song_repository(request: Request) -> SongRepository:
    return get_container(request).song_repository


def get_sync_snapshot_repository(request: Request) -> SyncSnapshotRepository:
    return get_container(request).sync_snapshot_repository


def get_soundcloud_playlist_importer(request: Request) -> SoundCloudPlaylistImporter:
    return get_container(request).soundcloud_playlist_importer
