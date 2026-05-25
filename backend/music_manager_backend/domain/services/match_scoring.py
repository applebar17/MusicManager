from dataclasses import replace
from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, MatchCandidate, SongMaster
from music_manager_backend.domain.services.title_normalizer import normalize_title

DURATION_TOLERANCE_SECONDS = 5
HIGH_CONFIDENCE_THRESHOLD = 0.95
PLAYLIST_PATH_CONFIDENCE = 0.95


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


def score_song_files(
    song: SongMaster,
    audio_files: list[AudioFile],
    *,
    playlist_names: set[str] | None = None,
) -> list[MatchCandidate]:
    scored = [
        (candidate, audio_file)
        for audio_file in audio_files
        if (candidate := score_song_file(song, audio_file)) is not None
    ]
    candidates = _with_playlist_path_tie_breaker(scored, playlist_names or set())
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


def _with_playlist_path_tie_breaker(
    scored: list[tuple[MatchCandidate, AudioFile]],
    playlist_names: set[str],
) -> list[MatchCandidate]:
    candidates = [candidate for candidate, _audio_file in scored]
    if len(scored) < 2:
        return candidates

    normalized_playlist_names = {
        normalized for name in playlist_names if (normalized := normalize_title(name))
    }
    if not normalized_playlist_names:
        return candidates

    top_confidence = max(candidate.confidence for candidate in candidates)
    if top_confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return candidates

    top_indexes = [
        index
        for index, (candidate, _audio_file) in enumerate(scored)
        if candidate.confidence == top_confidence
        and candidate.method in {"title_duration", "filename_title"}
    ]
    if len(top_indexes) < 2:
        return candidates

    matching_indexes = [
        index
        for index in top_indexes
        if _path_matches_playlist(scored[index][1].path, normalized_playlist_names)
    ]
    if len(matching_indexes) != 1:
        return candidates

    promoted_index = matching_indexes[0]
    promoted = candidates[promoted_index]
    candidates[promoted_index] = replace(
        promoted,
        method=f"playlist_path_{promoted.method}",
        confidence=PLAYLIST_PATH_CONFIDENCE,
    )
    return candidates


def _path_matches_playlist(path: Path, normalized_playlist_names: set[str]) -> bool:
    return any(normalize_title(part) in normalized_playlist_names for part in path.parent.parts)
