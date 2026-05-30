from pathlib import Path
from typing import Literal

from music_manager_backend.domain.entities import AudioFile, MusicEnvironment

AudioFileSourceArea = Literal["download", "usb", "other"]


def audio_file_source_area(
    environment: MusicEnvironment,
    audio_file: AudioFile,
) -> AudioFileSourceArea:
    return path_source_area(environment, audio_file.path)


def path_source_area(
    environment: MusicEnvironment,
    path: Path,
) -> AudioFileSourceArea:
    resolved = path.resolve(strict=False)
    if environment.download_path is not None:
        download_root = environment.download_path.resolve(strict=False)
        if resolved.is_relative_to(download_root):
            return "download"

    root = environment.root_path.resolve(strict=False)
    if resolved.is_relative_to(root):
        return "usb"
    return "other"


def path_is_inside(path: Path, root: Path) -> bool:
    return path.resolve(strict=False).is_relative_to(root.resolve(strict=False))
