from dataclasses import dataclass

from music_manager_backend.infrastructure.persistence import SqliteEnvironmentRepository
from music_manager_backend.shared.settings import Settings


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    environment_repository: SqliteEnvironmentRepository
