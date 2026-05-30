from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, MatchCandidate, SongMaster
from music_manager_backend.domain.services.audio_quality import is_likely_preview_duration
from music_manager_backend.domain.services.title_normalizer import (
    normalize_match_title,
    normalize_title,
    normalize_versionless_match_title,
)

STRICT_DURATION_TOLERANCE_SECONDS = 3
LOOSE_DURATION_TOLERANCE_SECONDS = 5
HIGH_CONFIDENCE_THRESHOLD = 0.95
PLAYLIST_PATH_CONFIDENCE = 0.96
VERSION_RELAXED_CONFIDENCE = 0.68
VERSION_RELAXED_CONTEXT_CONFIDENCE = 0.78


def score_song_file(song: SongMaster, audio_file: AudioFile) -> MatchCandidate | None:
    candidate = _score_song_file(song, audio_file)
    if candidate is not None and is_likely_preview_duration(audio_file.duration_seconds):
        return replace(
            candidate,
            method=f"likely_preview_{candidate.method}",
            confidence=0.0,
        )
    return candidate


def _score_song_file(song: SongMaster, audio_file: AudioFile) -> MatchCandidate | None:
    song_artist = normalize_match_title(song.display_artist or "")
    audio_artist = normalize_match_title(audio_file.artist or "")
    song_titles = _title_variants(
        song.display_title,
        song.display_artist,
        normalizer=normalize_match_title,
    )
    audio_titles = _title_variants(
        audio_file.title or "",
        audio_file.artist,
        song.display_artist,
        normalizer=normalize_match_title,
    )
    filename_titles = _title_variants(
        Path(audio_file.path).stem,
        audio_file.artist,
        song.display_artist,
        normalizer=normalize_match_title,
    )

    if (
        song_titles
        and _titles_overlap(song_titles, audio_titles)
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
        song_titles
        and _titles_overlap(song_titles, audio_titles)
        and _duration_within_strict_tolerance(song.duration_seconds, audio_file.duration_seconds)
    ):
        return MatchCandidate(
            audio_file_id=audio_file.id,
            method="title_strict_duration",
            confidence=0.95,
        )

    if (
        song_titles
        and _titles_overlap(song_titles, audio_titles)
        and _duration_within_loose_tolerance(song.duration_seconds, audio_file.duration_seconds)
    ):
        return MatchCandidate(
            audio_file_id=audio_file.id,
            method="title_duration",
            confidence=0.85,
        )

    if (
        song_titles
        and _titles_overlap(song_titles, audio_titles)
        and song.duration_seconds is not None
        and audio_file.duration_seconds is not None
    ):
        return None

    if _song_title_in_filename(song_titles, filename_titles):
        return MatchCandidate(
            audio_file_id=audio_file.id,
            method="filename_title",
            confidence=0.70,
        )

    version_candidate = _score_version_relaxed(song, audio_file, song_artist, audio_artist)
    if version_candidate is not None:
        return version_candidate

    return None


def _score_version_relaxed(
    song: SongMaster,
    audio_file: AudioFile,
    song_artist: str,
    audio_artist: str,
) -> MatchCandidate | None:
    if (
        song.duration_seconds is not None
        and audio_file.duration_seconds is not None
        and not _duration_within_loose_tolerance(song.duration_seconds, audio_file.duration_seconds)
    ):
        return None

    song_titles = _title_variants(
        song.display_title,
        song.display_artist,
        normalizer=normalize_versionless_match_title,
    )
    audio_titles = _title_variants(
        audio_file.title or "",
        audio_file.artist,
        song.display_artist,
        normalizer=normalize_versionless_match_title,
    )
    filename_titles = _title_variants(
        Path(audio_file.path).stem,
        audio_file.artist,
        song.display_artist,
        normalizer=normalize_versionless_match_title,
    )
    titles_match = _titles_overlap(song_titles, audio_titles)
    filename_matches = _song_title_in_filename(song_titles, filename_titles)
    if not titles_match and not filename_matches:
        return None

    has_context = (
        bool(song_artist and audio_artist == song_artist)
        or _duration_within_strict_tolerance(song.duration_seconds, audio_file.duration_seconds)
    )
    return MatchCandidate(
        audio_file_id=audio_file.id,
        method="version_relaxed_title" if titles_match else "version_relaxed_filename_title",
        confidence=(
            VERSION_RELAXED_CONTEXT_CONFIDENCE if has_context else VERSION_RELAXED_CONFIDENCE
        ),
    )


def _title_variants(
    value: str,
    *artists: str | None,
    normalizer: Callable[[str], str],
) -> set[str]:
    title = normalizer(value)
    variants = {title} if title else set()
    for raw_artist in artists:
        artist = normalizer(raw_artist or "")
        if artist and title.startswith(f"{artist} "):
            variants.add(title.removeprefix(artist).strip())
    return {variant for variant in variants if variant}


def _titles_overlap(song_titles: set[str], candidate_titles: set[str]) -> bool:
    return bool(song_titles & candidate_titles)


def _song_title_in_filename(song_titles: set[str], filename_titles: set[str]) -> bool:
    return any(
        song_title in filename_title
        for song_title in song_titles
        for filename_title in filename_titles
    )


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
    high_confidence = [item for item in candidates if item.confidence >= HIGH_CONFIDENCE_THRESHOLD]
    if not high_confidence:
        return False
    top_confidence = max(item.confidence for item in high_confidence)
    return sum(1 for item in high_confidence if item.confidence == top_confidence) == 1


def _duration_compatible(song_duration: int | None, file_duration: int | None) -> bool:
    if song_duration is None or file_duration is None:
        return True
    return _duration_within_loose_tolerance(song_duration, file_duration)


def _duration_within_strict_tolerance(
    song_duration: int | None, file_duration: int | None
) -> bool:
    if song_duration is None or file_duration is None:
        return False
    return abs(song_duration - file_duration) <= STRICT_DURATION_TOLERANCE_SECONDS


def _duration_within_loose_tolerance(song_duration: int | None, file_duration: int | None) -> bool:
    if song_duration is None or file_duration is None:
        return False
    return abs(song_duration - file_duration) <= LOOSE_DURATION_TOLERANCE_SECONDS


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
    top_indexes = [
        index
        for index, (candidate, _audio_file) in enumerate(scored)
        if candidate.confidence == top_confidence
        and candidate.method
        in {"metadata_exact", "title_strict_duration", "title_duration", "filename_title"}
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
