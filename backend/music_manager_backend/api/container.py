from dataclasses import dataclass

from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteScanRunRepository,
)
from music_manager_backend.shared.settings import Settings


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    audio_file_repository: SqliteAudioFileRepository
    environment_repository: SqliteEnvironmentRepository
    scan_run_repository: SqliteScanRunRepository
