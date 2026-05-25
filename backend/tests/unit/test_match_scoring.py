from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, SongMaster
from music_manager_backend.domain.services.match_scoring import score_song_file, score_song_files


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


def test_playlist_path_context_promotes_one_duplicate_review_candidate() -> None:
    song = SongMaster(
        id="song_1",
        title="Belpaese - Sentimento [Promo]",
        artist="Belpaese",
        duration_seconds=372,
    )
    pop_file = AudioFile(
        id="file_pop",
        environment_id="env_1",
        path=Path("/Volumes/TORDIS/08_POP/Belpaese - Sentimento [Promo].mp3"),
        size_bytes=1,
        modified_at=1.0,
        title="Belpaese - Sentimento [Promo]",
        artist="Gare du Nord",
        duration_seconds=373,
    )
    dance_file = AudioFile(
        id="file_dance",
        environment_id="env_1",
        path=Path("/Volumes/TORDIS/04_DANCE/Belpaese - Sentimento [Promo].mp3"),
        size_bytes=1,
        modified_at=1.0,
        title="Belpaese - Sentimento [Promo]",
        artist="Gare du Nord",
        duration_seconds=373,
    )

    candidates = score_song_files(
        song,
        [pop_file, dance_file],
        playlist_names={"04_DANCE"},
    )

    assert candidates[0].audio_file_id == "file_dance"
    assert candidates[0].method == "playlist_path_title_duration"
    assert candidates[0].confidence == 0.95
    assert candidates[1].audio_file_id == "file_pop"
    assert candidates[1].method == "title_duration"


def test_playlist_path_context_stays_ambiguous_when_multiple_folders_match() -> None:
    song = SongMaster(id="song_1", title="Track", duration_seconds=120)
    first = AudioFile(
        id="file_1",
        environment_id="env_1",
        path=Path("/Volumes/TORDIS/04_DANCE/Track.mp3"),
        size_bytes=1,
        modified_at=1.0,
        title="Track",
        duration_seconds=120,
    )
    second = AudioFile(
        id="file_2",
        environment_id="env_1",
        path=Path("/Volumes/TORDIS/04_DANCE/Sub/Track.mp3"),
        size_bytes=1,
        modified_at=1.0,
        title="Track",
        duration_seconds=120,
    )

    candidates = score_song_files(song, [first, second], playlist_names={"04_DANCE"})

    assert [candidate.method for candidate in candidates] == ["title_duration", "title_duration"]
