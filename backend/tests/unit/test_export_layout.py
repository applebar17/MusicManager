from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, MusicEnvironment, Playlist, SongMaster
from music_manager_backend.domain.services.export_layout import ExportLayout
from music_manager_backend.domain.services.filename_sanitizer import sanitize_path_part


def test_sanitize_path_part_removes_unsafe_characters() -> None:
    assert sanitize_path_part('Artist: Track / Mix?*') == "Artist Track Mix"
    assert sanitize_path_part("   ") == "Untitled"
    assert sanitize_path_part("CON") == "CON_"


def test_export_layout_generates_stable_managed_paths_with_collisions() -> None:
    environment = MusicEnvironment(
        id="env_1",
        name="USB",
        root_path=Path("/Volumes/USB"),
        deprecated_folder_name="_deprecated",
    )
    layout = ExportLayout(environment)
    first_playlist = Playlist(id="playlist_1", environment_id="env_1", name="A/B")
    second_playlist = Playlist(id="playlist_2", environment_id="env_1", name="A:B")
    song = SongMaster(id="song_1", title="Track/One", artist="Artist")
    audio_file = AudioFile(
        id="file_1",
        environment_id="env_1",
        path=Path("/Volumes/USB/source.mp3"),
        size_bytes=1,
        modified_at=1.0,
    )

    first_folder = layout.playlist_folder(first_playlist)
    second_folder = layout.playlist_folder(second_playlist)
    first_track = layout.track_target(
        folder=first_folder,
        position=1,
        song=song,
        audio_file=audio_file,
    )
    second_track = layout.track_target(
        folder=first_folder,
        position=1,
        song=song,
        audio_file=audio_file,
    )

    assert layout.managed_root == Path("/Volumes/USB")
    assert layout.metadata_root == Path("/Volumes/USB/_music_manager")
    assert first_folder == Path("/Volumes/USB/A B")
    assert second_folder == Path("/Volumes/USB/A B (2)")
    assert layout.playlist_folder(first_playlist) == first_folder
    assert first_track == first_folder / "source.mp3"
    assert second_track == first_folder / "source (2).mp3"
    assert layout.deprecated_target(song=song, audio_file=audio_file).as_posix().startswith(
        "/Volumes/USB/_music_manager/_deprecated/"
    )
