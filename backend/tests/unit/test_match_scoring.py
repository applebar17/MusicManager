from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, SongMaster
from music_manager_backend.domain.services.match_scoring import score_song_file


def test_metadata_exact_match_scores_high_confidence() -> None:
    song = SongMaster(id="song_1", title="Galactica Airlines", artist="Iden Kai")
    audio_file = AudioFile(
        id="file_1",
        environment_id="env_1",
        path=Path("/music/galactica.mp3"),
        size_bytes=1,
        modified_at=1.0,
        title="galactica airlines",
        artist="IDEN KAI",
    )

    candidate = score_song_file(song, audio_file)

    assert candidate is not None
    assert candidate.method == "metadata_exact"
    assert candidate.confidence == 0.95


def test_duration_tolerance_accepts_small_difference_and_rejects_large_one() -> None:
    song = SongMaster(id="song_1", title="Track", duration_seconds=120)
    close_file = AudioFile(
        id="file_1",
        environment_id="env_1",
        path=Path("/music/track.mp3"),
        size_bytes=1,
        modified_at=1.0,
        title="Track",
        duration_seconds=124,
    )
    far_file = AudioFile(
        id="file_2",
        environment_id="env_1",
        path=Path("/music/track-long.mp3"),
        size_bytes=1,
        modified_at=1.0,
        title="Track",
        duration_seconds=140,
    )

    close_candidate = score_song_file(song, close_file)

    assert close_candidate is not None
    assert close_candidate.method == "title_duration"
    assert score_song_file(song, far_file) is None


def test_filename_title_match_is_lower_confidence() -> None:
    song = SongMaster(id="song_1", title="Emotional Prism")
    audio_file = AudioFile(
        id="file_1",
        environment_id="env_1",
        path=Path("/music/Mikazuki - Emotional Prism.mp3"),
        size_bytes=1,
        modified_at=1.0,
    )

    candidate = score_song_file(song, audio_file)

    assert candidate is not None
    assert candidate.method == "filename_title"
    assert candidate.confidence == 0.70


def test_different_mix_title_does_not_auto_match() -> None:
    song = SongMaster(id="song_1", title="Track Original Mix", artist="Artist")
    audio_file = AudioFile(
        id="file_1",
        environment_id="env_1",
        path=Path("/music/Artist - Track Extended Mix.mp3"),
        size_bytes=1,
        modified_at=1.0,
        title="Track Extended Mix",
        artist="Artist",
    )

    assert score_song_file(song, audio_file) is None
