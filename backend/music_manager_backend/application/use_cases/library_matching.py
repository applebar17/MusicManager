from pathlib import Path

from music_manager_backend.application.dtos import (
    LibraryMatchingRunSummary,
    LibraryMatchReviewRow,
    LibraryTrackCandidateRead,
)
from music_manager_backend.application.use_cases.matching_common import load_environment_songs
from music_manager_backend.domain.entities import (
    LibraryMatchStatus,
    LibraryTrack,
    LibraryTrackStatus,
    SongLibraryLink,
    SongMaster,
)
from music_manager_backend.domain.services.title_normalizer import normalize_match_title
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    LibraryRepository,
    LibraryTrackRepository,
    PlaylistRepository,
    SongLibraryLinkRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class RunLibraryMatching:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
        song_library_links: SongLibraryLinkRepository,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.song_library_links = song_library_links

    def execute(self, environment_id: str) -> LibraryMatchingRunSummary:
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        library = self.libraries.get_default()
        if library is None:
            raise ValidationError("Shared library is not configured.")
        active_tracks = active_library_tracks_by_id(library.id, self.library_tracks)

        matched = 0
        missing = 0
        ambiguous = 0
        manual = 0

        for song in environment_songs.songs:
            accepted = preferred_library_link(
                self.song_library_links.list_by_song(song.id),
                active_tracks,
            )
            if accepted is not None and accepted.reviewed and accepted.method == "manual":
                manual += 1
                continue

            self.song_library_links.delete_automatic_by_song(song.id)
            candidates = identity_library_candidates(
                song=song,
                library_id=library.id,
                library_tracks=self.library_tracks,
            )
            if len(candidates) == 1:
                self.song_library_links.save(
                    SongLibraryLink(
                        song_id=song.id,
                        library_track_id=candidates[0].id,
                        method="library_identity_exact",
                        confidence=1.0,
                    )
                )
                matched += 1
            elif len(candidates) > 1:
                ambiguous += 1
            else:
                missing += 1

        return LibraryMatchingRunSummary(
            environment_id=environment_id,
            total=len(environment_songs.songs),
            matched=matched,
            missing_library=missing,
            ambiguous_library=ambiguous,
            manually_mapped_library=manual,
        )


class ListLibraryMatchReview:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
        song_library_links: SongLibraryLinkRepository,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.song_library_links = song_library_links

    def execute(self, environment_id: str) -> list[LibraryMatchReviewRow]:
        library = self.libraries.get_default()
        if library is None:
            raise ValidationError("Shared library is not configured.")
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        active_tracks = active_library_tracks_by_id(library.id, self.library_tracks)
        return [
            library_match_review_row(
                song=song,
                library_id=library.id,
                active_tracks=active_tracks,
                library_tracks=self.library_tracks,
                song_library_links=self.song_library_links,
            )
            for song in environment_songs.songs
        ]


class ListManualLibraryTrackCandidates:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
        song_library_links: SongLibraryLinkRepository,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.song_library_links = song_library_links

    def execute(
        self,
        environment_id: str,
        *,
        song_id: str,
        query: str = "",
    ) -> list[LibraryTrackCandidateRead]:
        library = self.libraries.get_default()
        if library is None:
            raise ValidationError("Shared library is not configured.")
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

        normalized_query = normalize_match_title(query)
        candidates: list[LibraryTrackCandidateRead] = []
        for track in self.library_tracks.list_by_status(library.id, LibraryTrackStatus.ACTIVE):
            identity_match = _identity_matches(song, track)
            query_match = _track_matches_query(track, normalized_query)
            if not identity_match and not query_match:
                continue
            if not normalized_query and not identity_match:
                continue
            candidates.append(
                library_track_candidate_read(
                    track,
                    method="library_identity_exact" if identity_match else "manual_search",
                    confidence=1.0 if identity_match else 0.0,
                )
            )

        return sorted(
            candidates,
            key=lambda item: (-item.confidence, item.filename.casefold(), item.library_track_id),
        )[:50]


class CreateManualLibraryMapping:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
        song_library_links: SongLibraryLinkRepository,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.song_library_links = song_library_links

    def execute(
        self,
        environment_id: str,
        song_id: str,
        library_track_id: str,
    ) -> LibraryMatchReviewRow:
        library = self.libraries.get_default()
        if library is None:
            raise ValidationError("Shared library is not configured.")
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        if song_id not in environment_songs.song_ids:
            raise NotFoundError(f"Song not found in environment: {song_id}")
        track = self.library_tracks.get(library_track_id)
        if track is None or track.library_id != library.id:
            raise ValidationError(f"Library track not found: {library_track_id}")
        if track.status != LibraryTrackStatus.ACTIVE:
            raise ValidationError(f"Library track is not active: {library_track_id}")

        self.song_library_links.replace_for_song(
            SongLibraryLink(
                song_id=song_id,
                library_track_id=library_track_id,
                method="manual",
                confidence=1.0,
                reviewed=True,
            )
        )
        song = self.songs.get(song_id)
        if song is None:
            raise NotFoundError(f"Song not found in environment: {song_id}")
        active_tracks = active_library_tracks_by_id(library.id, self.library_tracks)
        return library_match_review_row(
            song=song,
            library_id=library.id,
            active_tracks=active_tracks,
            library_tracks=self.library_tracks,
            song_library_links=self.song_library_links,
        )


def active_library_tracks_by_id(
    library_id: str,
    library_tracks: LibraryTrackRepository,
) -> dict[str, LibraryTrack]:
    return {
        track.id: track
        for track in library_tracks.list_by_status(library_id, LibraryTrackStatus.ACTIVE)
    }


def preferred_library_link(
    links: list[SongLibraryLink],
    active_tracks: dict[str, LibraryTrack],
) -> SongLibraryLink | None:
    active_links = [link for link in links if link.library_track_id in active_tracks]
    manual = [link for link in active_links if link.reviewed and link.method == "manual"]
    if manual:
        return manual[0]
    automatic = [link for link in active_links if not link.reviewed]
    if automatic:
        return automatic[0]
    return active_links[0] if active_links else None


def identity_library_candidates(
    *,
    song: SongMaster,
    library_id: str,
    library_tracks: LibraryTrackRepository,
) -> list[LibraryTrack]:
    normalized_title = normalize_match_title(song.display_title)
    if not normalized_title or song.duration_seconds is None:
        return []
    return library_tracks.get_by_identity(library_id, normalized_title, song.duration_seconds)


def library_match_review_row(
    *,
    song: SongMaster,
    library_id: str,
    active_tracks: dict[str, LibraryTrack],
    library_tracks: LibraryTrackRepository,
    song_library_links: SongLibraryLinkRepository,
) -> LibraryMatchReviewRow:
    links = song_library_links.list_by_song(song.id)
    accepted = preferred_library_link(links, active_tracks)
    if accepted is not None:
        track = active_tracks[accepted.library_track_id]
        status = (
            LibraryMatchStatus.MANUALLY_MAPPED_LIBRARY
            if accepted.reviewed and accepted.method == "manual"
            else LibraryMatchStatus.LIBRARY_MATCHED
        )
        return LibraryMatchReviewRow(
            song_id=song.id,
            title=song.display_title,
            artist=song.display_artist,
            duration_seconds=song.duration_seconds,
            status=status.value,
            match=library_track_candidate_read(
                track,
                method=accepted.method,
                confidence=accepted.confidence,
            ),
            candidates=[],
        )

    candidates = identity_library_candidates(
        song=song,
        library_id=library_id,
        library_tracks=library_tracks,
    )
    status = (
        LibraryMatchStatus.AMBIGUOUS_LIBRARY
        if len(candidates) > 1
        else LibraryMatchStatus.MISSING_LIBRARY
    )
    return LibraryMatchReviewRow(
        song_id=song.id,
        title=song.display_title,
        artist=song.display_artist,
        duration_seconds=song.duration_seconds,
        status=status.value,
        candidates=[
            library_track_candidate_read(
                track,
                method="library_identity_exact",
                confidence=1.0,
            )
            for track in candidates
        ],
    )


def library_track_candidate_read(
    track: LibraryTrack,
    *,
    method: str,
    confidence: float,
) -> LibraryTrackCandidateRead:
    return LibraryTrackCandidateRead(
        library_track_id=track.id,
        path=str(track.canonical_path),
        filename=track.filename,
        title=track.title,
        artist=track.artist,
        duration_seconds=track.duration_seconds,
        method=method,
        confidence=confidence,
    )


def _identity_matches(song: SongMaster, track: LibraryTrack) -> bool:
    normalized_title = normalize_match_title(song.display_title)
    return (
        bool(normalized_title)
        and normalized_title == track.normalized_title
        and song.duration_seconds is not None
        and song.duration_seconds == track.duration_seconds
    )


def _track_matches_query(track: LibraryTrack, normalized_query: str) -> bool:
    if not normalized_query:
        return False
    path = Path(track.canonical_path)
    haystack = [
        normalize_match_title(path.name),
        normalize_match_title(path.stem),
        normalize_match_title(str(path)),
        normalize_match_title(track.filename),
        normalize_match_title(track.title or ""),
        normalize_match_title(track.artist or ""),
    ]
    query_tokens = normalized_query.split()
    return any(
        normalized_query in value or all(token in value.split() for token in query_tokens)
        for value in haystack
        if value
    )
