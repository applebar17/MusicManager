from music_manager_backend.domain.entities import AudioFile
from music_manager_backend.ports.filesystem import AudioFileScanner


class ScanEnvironment:
    def __init__(self, scanner: AudioFileScanner) -> None:
        self.scanner = scanner

    def execute(self, environment_id: str) -> list[AudioFile]:
        return self.scanner.scan(environment_id)

