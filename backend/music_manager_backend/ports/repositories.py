from typing import Protocol

from music_manager_backend.domain.entities import MusicEnvironment


class EnvironmentRepository(Protocol):
    def save(self, environment: MusicEnvironment) -> None:
        pass

    def list(self) -> list[MusicEnvironment]:
        pass

