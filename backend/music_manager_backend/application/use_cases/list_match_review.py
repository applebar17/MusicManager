from music_manager_backend.application.dtos import MatchReviewRow
from music_manager_backend.application.use_cases.discover_soundcloud_track import (
    stored_discovery_read,
)
from music_manager_backend.application.use_cases.matching_common import (
    load_environment_songs,
)
from music_manager_backend.application.use_cases.library_matching import (
    active_library_tracks_by_id,
    library_match_review_row,
)
from music_manager_backend.domain.entities import (
    LibraryMatchStatus,
    LibraryTrack,
    MatchStatus,
    SongMaster,
)
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    LibraryRepository,
    LibraryTrackRepository,
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
        source_discoveries: SourceDiscoveryRepository | None = None,
        libraries: LibraryRepository | None = None,
        library_tracks: LibraryTrackRepository | None = None,
        song_library_links: SongLibraryLinkRepository | None = None,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
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
            rows.append(
                MatchReviewRow(
                    song_id=song.id,
                    title=song.display_title,
                    artist=song.display_artist,
                    duration_seconds=song.duration_seconds,
                    status=_legacy_status_from_library_status(library_fields["library_status"]),
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


def _legacy_status_from_library_status(status: object) -> str:
    if status == LibraryMatchStatus.LIBRARY_MATCHED.value:
        return MatchStatus.MATCHED.value
    if status == LibraryMatchStatus.MANUALLY_MAPPED_LIBRARY.value:
        return MatchStatus.MANUALLY_MAPPED.value
    if status == LibraryMatchStatus.AMBIGUOUS_LIBRARY.value:
        return MatchStatus.AMBIGUOUS.value
    return MatchStatus.MISSING_AUDIO.value
