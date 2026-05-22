from pathlib import Path

from music_manager_backend.domain.entities import DiscoveredAudioFile

SUPPORTED_AUDIO_EXTENSIONS = {".aiff", ".flac", ".m4a", ".mp3", ".wav"}


class LocalAudioScanner:
    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path

    def scan(self) -> list[DiscoveredAudioFile]:
        files: list[DiscoveredAudioFile] = []
        for path in self.root_path.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in SUPPORTED_AUDIO_EXTENSIONS:
                continue

            stat = path.stat()
            files.append(
                DiscoveredAudioFile(
                    path=path,
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )
        return files
