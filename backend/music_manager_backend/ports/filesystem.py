from typing import Protocol

from music_manager_backend.domain.entities import DiscoveredAudioFile


class AudioFileScanner(Protocol):
    def scan(self) -> list[DiscoveredAudioFile]:
        pass
