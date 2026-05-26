import sqlite3
from dataclasses import dataclass
from pathlib import Path

from music_manager_backend.api.operation_coordinator import OperationCoordinator
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteExportApplyRunRepository,
    SqliteExportPlanRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteRemotePlaylistRepository,
    SqliteScanRunRepository,
    SqliteSongRepository,
    SqliteSyncSnapshotRepository,
)
from music_manager_backend.infrastructure.persistence.sqlite import connect
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter
from music_manager_backend.shared.settings import Settings


@dataclass
class SqliteRepositoryBundle:
    connection: sqlite3.Connection
    audio_file_repository: SqliteAudioFileRepository
    environment_repository: SqliteEnvironmentRepository
    export_apply_run_repository: SqliteExportApplyRunRepository
    export_plan_repository: SqliteExportPlanRepository
    match_link_repository: SqliteMatchLinkRepository
    playlist_repository: SqlitePlaylistRepository
    remote_playlist_repository: SqliteRemotePlaylistRepository
    scan_run_repository: SqliteScanRunRepository
    song_repository: SqliteSongRepository
    sync_snapshot_repository: SqliteSyncSnapshotRepository

    @classmethod
    def open(cls, database_path: Path) -> "SqliteRepositoryBundle":
        connection = connect(database_path)
        return cls(
            connection=connection,
            audio_file_repository=SqliteAudioFileRepository(connection),
            environment_repository=SqliteEnvironmentRepository(connection),
            export_apply_run_repository=SqliteExportApplyRunRepository(connection),
            export_plan_repository=SqliteExportPlanRepository(connection),
            match_link_repository=SqliteMatchLinkRepository(connection),
            playlist_repository=SqlitePlaylistRepository(connection),
            remote_playlist_repository=SqliteRemotePlaylistRepository(connection),
            scan_run_repository=SqliteScanRunRepository(connection),
            song_repository=SqliteSongRepository(connection),
            sync_snapshot_repository=SqliteSyncSnapshotRepository(connection),
        )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SqliteRepositoryBundle":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    soundcloud_playlist_importer: SoundCloudPlaylistImporter
    operation_coordinator: OperationCoordinator

    def repository_bundle(self) -> SqliteRepositoryBundle:
        return SqliteRepositoryBundle.open(self.settings.database_path)
