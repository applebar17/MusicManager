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


def test_scanner_skips_app_and_system_directories(
    music_environment_root: Path,
) -> None:
    app_copy = music_environment_root / ".music_manager" / "_deprecated" / "old.mp3"
    system_copy = music_environment_root / "System Volume Information" / "system.mp3"
    real_track = music_environment_root / "01_TECH" / "track.mp3"
    for path in (app_copy, system_copy, real_track):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")

    discovered = LocalAudioScanner(music_environment_root).scan()

    assert {item.path for item in discovered} == {real_track}


def test_scanner_does_not_follow_symlink_directories(
    tmp_path: Path,
    music_environment_root: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_track = outside / "outside.mp3"
    outside_track.write_bytes(b"audio")
    linked = music_environment_root / "linked"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        return

    discovered = LocalAudioScanner(music_environment_root).scan()

    assert discovered == []
