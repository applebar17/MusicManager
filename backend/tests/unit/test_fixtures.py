from collections.abc import Callable
from pathlib import Path


def test_music_environment_root_fixture_creates_isolated_folder(
    music_environment_root: Path,
) -> None:
    assert music_environment_root.exists()
    assert music_environment_root.is_dir()


def test_audio_file_fixture_creates_supported_file(
    create_audio_file: Callable[[str], Path],
    music_environment_root: Path,
) -> None:
    path = create_audio_file("nested/track.mp3")

    assert path.exists()
    assert path.parent == music_environment_root / "nested"
    assert path.suffix == ".mp3"


def test_unsupported_file_fixture_creates_non_audio_file(
    create_unsupported_file: Callable[[str], Path],
) -> None:
    path = create_unsupported_file("notes.txt")

    assert path.exists()
    assert path.suffix == ".txt"
