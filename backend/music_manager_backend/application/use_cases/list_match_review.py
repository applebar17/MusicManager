from music_manager_backend.application.dtos import MatchCandidateRead, MatchReviewRow
from music_manager_backend.application.use_cases.matching_common import (
    active_audio_files_by_id,
    candidate_audio_file,
    load_environment_songs,
)
from music_manager_backend.domain.entities import AudioFile, MatchCandidate, MatchLink, MatchStatus
from music_manager_backend.domain.services.match_scoring import score_song_files
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
)


class ListMatchReview:
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

    def execute(self, environment_id: str) -> list[MatchReviewRow]:
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        active_files = active_audio_files_by_id(
            environment_id=environment_id, audio_files=self.audio_files
        )
        active_file_list = list(active_files.values())

        rows: list[MatchReviewRow] = []
        for song in environment_songs.songs:
            links = self.match_links.list_by_song(song.id)
            accepted = _accepted_link(links, active_files)
            if accepted is not None:
                status = (
                    MatchStatus.MANUALLY_MAPPED
                    if accepted.reviewed and accepted.method == "manual"
                    else MatchStatus.MATCHED
                )
                rows.append(
                    MatchReviewRow(
                        song_id=song.id,
                        title=song.display_title,
                        artist=song.display_artist,
                        duration_seconds=song.duration_seconds,
                        status=status.value,
                        match=_candidate_from_link(accepted, active_files),
                        candidates=[],
                    )
                )
                continue

            candidates = score_song_files(song, active_file_list)
            rows.append(
                MatchReviewRow(
                    song_id=song.id,
                    title=song.display_title,
                    artist=song.display_artist,
                    duration_seconds=song.duration_seconds,
                    status=(
                        MatchStatus.AMBIGUOUS.value
                        if candidates
                        else MatchStatus.MISSING_AUDIO.value
                    ),
                    candidates=[
                        _candidate_from_candidate(candidate, active_files)
                        for candidate in candidates
                        if candidate_audio_file(candidate, active_files) is not None
                    ],
                )
            )
        return rows


def _accepted_link(
    links: list[MatchLink], active_files: dict[str, AudioFile]
) -> MatchLink | None:
    manual = [
        link
        for link in links
        if link.reviewed and link.method == "manual" and link.audio_file_id in active_files
    ]
    if manual:
        return manual[0]
    automatic = [
        link
        for link in links
        if not link.reviewed and link.audio_file_id in active_files
    ]
    return automatic[0] if automatic else None


def _candidate_from_link(
    link: MatchLink, active_files: dict[str, AudioFile]
) -> MatchCandidateRead:
    audio_file = active_files[link.audio_file_id]
    return MatchCandidateRead(
        audio_file_id=audio_file.id,
        path=str(audio_file.path),
        title=audio_file.title,
        artist=audio_file.artist,
        duration_seconds=audio_file.duration_seconds,
        method=link.method,
        confidence=link.confidence,
    )


def _candidate_from_candidate(
    candidate: MatchCandidate, active_files: dict[str, AudioFile]
) -> MatchCandidateRead:
    audio_file = active_files[candidate.audio_file_id]
    return MatchCandidateRead(
        audio_file_id=audio_file.id,
        path=str(audio_file.path),
        title=audio_file.title,
        artist=audio_file.artist,
        duration_seconds=audio_file.duration_seconds,
        method=candidate.method,
        confidence=candidate.confidence,
    )
