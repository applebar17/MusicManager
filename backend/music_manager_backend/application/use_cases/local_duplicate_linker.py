from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, MatchLink, SongMaster
from music_manager_backend.domain.services.audio_quality import is_likely_preview_duration
from music_manager_backend.domain.services.title_normalizer import normalize_title
from music_manager_backend.ports.repositories import MatchLinkRepository

LOCAL_DUPLICATE_METHOD = "local_duplicate"
LOCAL_DUPLICATE_CONFIDENCE = 0.99
LOCAL_DUPLICATE_DURATION_TOLERANCE_SECONDS = 3


def link_local_duplicate_files(
    *,
    song: SongMaster,
    anchor_file: AudioFile,
    active_files: dict[str, AudioFile],
    match_links: MatchLinkRepository,
) -> list[MatchLink]:
    if is_likely_preview_duration(anchor_file.duration_seconds):
        return []

    existing_audio_file_ids = {
        link.audio_file_id for link in match_links.list_by_song(song.id)
    }
    links: list[MatchLink] = []
    for audio_file in active_files.values():
        if audio_file.id == anchor_file.id:
            continue
        if audio_file.id in existing_audio_file_ids:
            continue
        if not _is_duplicate_audio_file(anchor_file, audio_file):
            continue
        link = MatchLink(
            song_id=song.id,
            audio_file_id=audio_file.id,
            method=LOCAL_DUPLICATE_METHOD,
            confidence=LOCAL_DUPLICATE_CONFIDENCE,
            reviewed=True,
        )
        match_links.save(link)
        links.append(link)
    return links


def _is_duplicate_audio_file(anchor: AudioFile, candidate: AudioFile) -> bool:
    if is_likely_preview_duration(candidate.duration_seconds):
        return False
    anchor_title = normalize_title(anchor.title or Path(anchor.path).stem)
    candidate_title = normalize_title(candidate.title or Path(candidate.path).stem)
    anchor_artist = normalize_title(anchor.artist or "")
    candidate_artist = normalize_title(candidate.artist or "")
    if not anchor_title or anchor_title != candidate_title:
        return False
    if anchor.duration_seconds is None or candidate.duration_seconds is None:
        return False
    if (
        abs(anchor.duration_seconds - candidate.duration_seconds)
        > LOCAL_DUPLICATE_DURATION_TOLERANCE_SECONDS
    ):
        return False

    if anchor_artist and candidate_artist:
        return anchor_artist == candidate_artist

    anchor_stem = normalize_title(Path(anchor.path).stem)
    candidate_stem = normalize_title(Path(candidate.path).stem)
    return bool(anchor_stem and anchor_stem == candidate_stem)
