from music_manager_backend.application.dtos import MatchCandidateRead, MatchReviewRow
from music_manager_backend.application.use_cases.audio_file_area import audio_file_source_area
from music_manager_backend.application.use_cases.discover_soundcloud_track import (
    stored_discovery_read,
)
from music_manager_backend.application.use_cases.match_link_selection import preferred_match_link
from music_manager_backend.application.use_cases.matching_common import (
    active_audio_files_by_id,
    candidate_audio_file,
    load_environment_songs,
)
from music_manager_backend.application.use_cases.library_matching import (
    active_library_tracks_by_id,
    library_match_review_row,
)
from music_manager_backend.domain.entities import (
    AudioFile,
    LibraryTrack,
    MatchCandidate,
    MatchLink,
    MatchStatus,
    MusicEnvironment,
    SongMaster,
)
from music_manager_backend.domain.services.audio_quality import audio_warnings
from music_manager_backend.domain.services.match_scoring import score_song_files
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    LibraryRepository,
    LibraryTrackRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongLibraryLinkRepository,
    SongRepository,
    SourceDiscoveryRepository,
)
from music_manager_backend.shared.errors import NotFoundError


class ListMatchReview:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
        source_discoveries: SourceDiscoveryRepository | None = None,
        libraries: LibraryRepository | None = None,
        library_tracks: LibraryTrackRepository | None = None,
        song_library_links: SongLibraryLinkRepository | None = None,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links
        self.source_discoveries = source_discoveries
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.song_library_links = song_library_links

    def execute(self, environment_id: str) -> list[MatchReviewRow]:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
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
        library = self.libraries.get_default() if self.libraries is not None else None
        active_library_tracks = (
            active_library_tracks_by_id(library.id, self.library_tracks)
            if library is not None and self.library_tracks is not None
            else {}
        )

        rows: list[MatchReviewRow] = []
        for song in environment_songs.songs:
            library_fields = _library_fields(
                song=song,
                library_id=library.id if library is not None else None,
                active_tracks=active_library_tracks,
                library_tracks=self.library_tracks,
                song_library_links=self.song_library_links,
            )
            links = self.match_links.list_by_song(song.id)
            accepted = preferred_match_link(links, active_files)
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
                        match=_candidate_from_link(accepted, active_files, environment),
                        candidates=[],
                        **library_fields,
                        source_discovery=(
                            stored_discovery_read(
                                environment_id=environment_id,
                                song=song,
                                source_discoveries=self.source_discoveries,
                            )
                            if self.source_discoveries is not None
                            else None
                        ),
                    )
                )
                continue

            candidates = score_song_files(
                song,
                active_file_list,
                playlist_names=environment_songs.playlist_names_by_song_id.get(song.id),
            )
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
                        _candidate_from_candidate(candidate, active_files, environment)
                        for candidate in candidates
                        if candidate_audio_file(candidate, active_files) is not None
                    ],
                    **library_fields,
                    source_discovery=(
                        stored_discovery_read(
                            environment_id=environment_id,
                            song=song,
                            source_discoveries=self.source_discoveries,
                        )
                        if self.source_discoveries is not None
                        else None
                    ),
                )
            )
        return rows


def _library_fields(
    *,
    song: SongMaster,
    library_id: str | None,
    active_tracks: dict[str, LibraryTrack],
    library_tracks: LibraryTrackRepository | None,
    song_library_links: SongLibraryLinkRepository | None,
) -> dict[str, object]:
    if library_id is None or library_tracks is None or song_library_links is None:
        return {
            "library_status": None,
            "library_match": None,
            "library_candidates": [],
        }
    row = library_match_review_row(
        song=song,
        library_id=library_id,
        active_tracks=active_tracks,
        library_tracks=library_tracks,
        song_library_links=song_library_links,
    )
    return {
        "library_status": row.status,
        "library_match": row.match,
        "library_candidates": row.candidates,
    }


def _candidate_from_link(
    link: MatchLink, active_files: dict[str, AudioFile], environment: MusicEnvironment
) -> MatchCandidateRead:
    audio_file = active_files[link.audio_file_id]
    return MatchCandidateRead(
        audio_file_id=audio_file.id,
        path=str(audio_file.path),
        source_area=audio_file_source_area(environment, audio_file),
        title=audio_file.title,
        artist=audio_file.artist,
        duration_seconds=audio_file.duration_seconds,
        method=link.method,
        confidence=link.confidence,
        warnings=audio_warnings(audio_file.duration_seconds),
    )


def _candidate_from_candidate(
    candidate: MatchCandidate, active_files: dict[str, AudioFile], environment: MusicEnvironment
) -> MatchCandidateRead:
    audio_file = active_files[candidate.audio_file_id]
    return MatchCandidateRead(
        audio_file_id=audio_file.id,
        path=str(audio_file.path),
        source_area=audio_file_source_area(environment, audio_file),
        title=audio_file.title,
        artist=audio_file.artist,
        duration_seconds=audio_file.duration_seconds,
        method=candidate.method,
        confidence=candidate.confidence,
        warnings=audio_warnings(audio_file.duration_seconds),
    )
