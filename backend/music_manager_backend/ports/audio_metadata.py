from pathlib import Path
from typing import Protocol

from music_manager_backend.domain.entities import AudioMetadata


class AudioMetadataReader(Protocol):
    def read(self, path: Path) -> AudioMetadata:
        pass
