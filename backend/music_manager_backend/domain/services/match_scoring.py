from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, MatchCandidate, SongMaster
from music_manager_backend.domain.services.title_normalizer import normalize_title

DURATION_TOLERANCE_SECONDS = 5
HIGH_CONFIDENCE_THRESHOLD = 0.95


def score_song_file(song: SongMaster, audio_file: AudioFile) -> MatchCandidate | None:
    song_title = normalize_title(song.display_title)
    song_artist = normalize_title(song.display_artist or "")
    audio_title = normalize_title(audio_file.title or "")
    audio_artist = normalize_title(audio_file.artist or "")
    filename = normalize_title(Path(audio_file.path).stem)

    if (
        song_title
        and audio_title == song_title
        and song_artist
        and audio_artist == song_artist
        and _duration_compatible(song.duration_seconds, audio_file.duration_seconds)
    ):
        return MatchCandidate(
            audio_file_id=audio_file.id,
            method="metadata_exact",
            confidence=0.95,
        )

    if (
        song_title
        and audio_title == song_title
        and _duration_within_tolerance(song.duration_seconds, audio_file.duration_seconds)
    ):
        return MatchCandidate(
            audio_file_id=audio_file.id,
            method="title_duration",
            confidence=0.85,
        )

    if (
        song_title
        and audio_title == song_title
        and song.duration_seconds is not None
        and audio_file.duration_seconds is not None
    ):
        return None

    if song_title and song_title in filename:
        return MatchCandidate(
            audio_file_id=audio_file.id,
            method="filename_title",
            confidence=0.70,
        )

    return None


def score_song_files(song: SongMaster, audio_files: list[AudioFile]) -> list[MatchCandidate]:
    candidates = [
        candidate
        for audio_file in audio_files
        if (candidate := score_song_file(song, audio_file)) is not None
    ]
    return sorted(candidates, key=lambda item: (-item.confidence, item.audio_file_id))


def is_unique_high_confidence(candidates: list[MatchCandidate]) -> bool:
    high_confidence = [
        item for item in candidates if item.confidence >= HIGH_CONFIDENCE_THRESHOLD
    ]
    return len(high_confidence) == 1


def _duration_compatible(song_duration: int | None, file_duration: int | None) -> bool:
    if song_duration is None or file_duration is None:
        return True
    return _duration_within_tolerance(song_duration, file_duration)


def _duration_within_tolerance(song_duration: int | None, file_duration: int | None) -> bool:
    if song_duration is None or file_duration is None:
        return False
    return abs(song_duration - file_duration) <= DURATION_TOLERANCE_SECONDS
