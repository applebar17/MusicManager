from typing import Protocol

from music_manager_backend.domain.entities import AudioFile


class AudioFileScanner(Protocol):
    def scan(self, environment_id: str) -> list[AudioFile]:
        pass

