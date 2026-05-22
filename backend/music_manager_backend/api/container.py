from dataclasses import dataclass

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
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter
from music_manager_backend.shared.settings import Settings


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
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
    soundcloud_playlist_importer: SoundCloudPlaylistImporter
