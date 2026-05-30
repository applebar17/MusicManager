from pathlib import Path

from music_manager_backend.application.dtos import MatchCandidateRead
from music_manager_backend.application.use_cases.audio_file_area import audio_file_source_area
from music_manager_backend.application.use_cases.match_link_selection import active_match_links
from music_manager_backend.application.use_cases.matching_common import (
    active_audio_files_by_id,
    load_environment_songs,
)
from music_manager_backend.domain.entities import AudioFile
from music_manager_backend.domain.services.audio_quality import audio_warnings
from music_manager_backend.domain.services.match_scoring import score_song_file
from music_manager_backend.domain.services.title_normalizer import normalize_match_title
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError


class ListManualAudioFileCandidates:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links

    def execute(
        self,
        environment_id: str,
        *,
        song_id: str,
        query: str = "",
    ) -> list[MatchCandidateRead]:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        if song_id not in environment_songs.song_ids:
            raise NotFoundError(f"Song not found in environment: {song_id}")
        song = self.songs.get(song_id)
        if song is None:
            raise NotFoundError(f"Song not found in environment: {song_id}")

        active_files = active_audio_files_by_id(
            environment_id=environment_id,
            audio_files=self.audio_files,
        )
        linked_elsewhere_ids = _linked_elsewhere_audio_file_ids(
            song_id=song_id,
            songs=[item.id for item in environment_songs.songs],
            active_files=active_files,
            match_links=self.match_links,
        )
        normalized_query = normalize_match_title(query)
        candidates: list[MatchCandidateRead] = []

        for audio_file in active_files.values():
            source_area = audio_file_source_area(environment, audio_file)
            if source_area not in {"usb", "download"}:
                continue
            if audio_file.id in linked_elsewhere_ids:
                continue

            scored = score_song_file(song, audio_file)
            matches_query = _audio_file_matches_query(audio_file, normalized_query)
            if scored is None and not matches_query:
                continue
            if not normalized_query and scored is None:
                continue

            candidates.append(
                MatchCandidateRead(
                    audio_file_id=audio_file.id,
                    path=str(audio_file.path),
                    source_area=source_area,
                    title=audio_file.title,
                    artist=audio_file.artist,
                    duration_seconds=audio_file.duration_seconds,
                    method=scored.method if scored is not None else "manual_search",
                    confidence=scored.confidence if scored is not None else 0.0,
                    warnings=audio_warnings(audio_file.duration_seconds),
                )
            )

        return sorted(
            candidates,
            key=lambda item: (
                -item.confidence,
                _source_area_rank(item.source_area),
                item.path.casefold(),
                item.audio_file_id,
            ),
        )[:50]


def _linked_elsewhere_audio_file_ids(
    *,
    song_id: str,
    songs: list[str],
    active_files: dict[str, AudioFile],
    match_links: MatchLinkRepository,
) -> set[str]:
    linked: set[str] = set()
    for current_song_id in songs:
        if current_song_id == song_id:
            continue
        linked.update(
            link.audio_file_id
            for link in active_match_links(match_links.list_by_song(current_song_id), active_files)
        )
    return linked


def _audio_file_matches_query(audio_file: AudioFile, normalized_query: str) -> bool:
    if not normalized_query:
        return False
    path = Path(audio_file.path)
    haystack = [
        normalize_match_title(path.name),
        normalize_match_title(path.stem),
        normalize_match_title(str(path)),
        normalize_match_title(audio_file.title or ""),
        normalize_match_title(audio_file.artist or ""),
        normalize_match_title(audio_file.album or ""),
    ]
    query_tokens = normalized_query.split()
    return any(
        normalized_query in value or all(token in value.split() for token in query_tokens)
        for value in haystack
        if value
    )


def _source_area_rank(source_area: str) -> int:
    if source_area == "download":
        return 0
    if source_area == "usb":
        return 1
    return 2
