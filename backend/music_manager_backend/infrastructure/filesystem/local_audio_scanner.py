import os
from pathlib import Path

from music_manager_backend.domain.entities import DiscoveredAudioFile
from music_manager_backend.domain.services.export_layout import EXPORT_METADATA_FOLDER_NAME
from music_manager_backend.infrastructure.filesystem.path_safety import validate_readable_directory

SUPPORTED_AUDIO_EXTENSIONS = {".aiff", ".flac", ".m4a", ".mp3", ".wav"}
IGNORED_DIRECTORY_NAMES = {
    EXPORT_METADATA_FOLDER_NAME,
    "$RECYCLE.BIN",
    ".Spotlight-V100",
    ".Trashes",
    ".fseventsd",
    "System Volume Information",
}


class LocalAudioScanner:
    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path

    def scan(self) -> list[DiscoveredAudioFile]:
        root = validate_readable_directory(self.root_path)
        files: list[DiscoveredAudioFile] = []
        directories = [root]
        while directories:
            directory = directories.pop()
            for entry in _iter_directory(directory):
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in IGNORED_DIRECTORY_NAMES:
                            directories.append(Path(entry.path))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    path = Path(entry.path)
                    if path.suffix.casefold() not in SUPPORTED_AUDIO_EXTENSIONS:
                        continue
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue

                files.append(
                    DiscoveredAudioFile(
                        path=path,
                        size_bytes=stat.st_size,
                        modified_at=stat.st_mtime,
                    )
                )
        return files


def _iter_directory(directory: Path) -> list[os.DirEntry[str]]:
    try:
        with os.scandir(directory) as entries:
            return sorted(entries, key=lambda entry: entry.name.casefold())
    except OSError:
        return []
