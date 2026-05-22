from collections.abc import Callable
from pathlib import Path

from music_manager_backend.infrastructure.filesystem import LocalAudioScanner


def test_scanner_finds_supported_files_recursively(
    create_audio_file: Callable[[str], Path],
    create_unsupported_file: Callable[[str], Path],
    music_environment_root: Path,
) -> None:
    mp3 = create_audio_file("nested/track.mp3")
    wav = create_audio_file("track.wav")
    create_unsupported_file("notes.txt")

    discovered = LocalAudioScanner(music_environment_root).scan()

    assert {item.path for item in discovered} == {mp3, wav}
