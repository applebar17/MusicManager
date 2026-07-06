import sqlite3
from pathlib import Path

from music_manager_backend.application.use_cases.library_matching import (
    CreateManualLibraryMapping,
    ListLibraryMatchReview,
    RunLibraryMatching,
)
from music_manager_backend.domain.entities import (
    LibraryTrack,
    LibraryTrackStatus,
    MusicEnvironment,
    MusicLibrary,
    Playlist,
    PlaylistItem,
    SongLibraryLink,
    SongMaster,
)
from music_manager_backend.infrastructure.persistence import (
    SqliteEnvironmentRepository,
    SqliteLibraryRepository,
    SqliteLibraryTrackRepository,
    SqlitePlaylistRepository,
    SqliteSongRepository,
    SqliteSongLibraryLinkRepository,
)


def test_library_matching_maps_exact_identity(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_environment_song_and_library(repositories)
    _save_track(repositories, "library_track_1", title="Track", duration_seconds=180)

    summary = _run_library_matching(repositories).execute("env_1")
    review = _list_library_review(repositories).execute("env_1")

    assert summary.matched == 1
    assert summary.missing_library == 0
    assert review[0].status == "library_matched"
    assert review[0].match is not None
    assert review[0].match.library_track_id == "library_track_1"


def test_library_matching_marks_duplicate_identity_ambiguous(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_environment_song_and_library(repositories)
    _save_track(repositories, "library_track_1", title="Track", duration_seconds=180)
    _save_track(repositories, "library_track_2", title="Track", duration_seconds=180)

    summary = _run_library_matching(repositories).execute("env_1")
    review = _list_library_review(repositories).execute("env_1")

    assert summary.ambiguous_library == 1
    assert repositories.song_library_links.list_by_song("song_1") == []
    assert review[0].status == "ambiguous_library"
    assert [candidate.library_track_id for candidate in review[0].candidates] == [
        "library_track_1",
        "library_track_2",
    ]


def test_library_matching_ignores_missing_tracks(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_environment_song_and_library(repositories)
    _save_track(
        repositories,
        "library_track_1",
        title="Track",
        duration_seconds=180,
        status=LibraryTrackStatus.MISSING,
    )

    summary = _run_library_matching(repositories).execute("env_1")

    assert summary.missing_library == 1
    assert repositories.song_library_links.list_by_song("song_1") == []


def test_manual_library_mapping_overrides_and_survives_rerun(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_environment_song_and_library(repositories)
    _save_track(repositories, "library_track_1", title="Other", duration_seconds=180)
    _save_track(repositories, "library_track_2", title="Track", duration_seconds=180)

    row = _manual_library_mapping(repositories).execute("env_1", "song_1", "library_track_1")
    summary = _run_library_matching(repositories).execute("env_1")
    links = repositories.song_library_links.list_by_song("song_1")

    assert row.status == "manually_mapped_library"
    assert summary.manually_mapped_library == 1
    assert links == [
        SongLibraryLink(
            song_id="song_1",
            library_track_id="library_track_1",
            method="manual",
            confidence=1.0,
            reviewed=True,
            created_at=links[0].created_at,
            updated_at=links[0].updated_at,
        )
    ]


class _Repositories:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.environments = SqliteEnvironmentRepository(connection)
        self.playlists = SqlitePlaylistRepository(connection)
        self.songs = SqliteSongRepository(connection)
        self.libraries = SqliteLibraryRepository(connection)
        self.library_tracks = SqliteLibraryTrackRepository(connection)
        self.song_library_links = SqliteSongLibraryLinkRepository(connection)


def _repositories(connection: sqlite3.Connection) -> _Repositories:
    return _Repositories(connection)


def _seed_environment_song_and_library(repositories: _Repositories) -> None:
    repositories.environments.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    repositories.songs.save(
        SongMaster(id="song_1", title="Track", artist="Artist", duration_seconds=180)
    )
    repositories.playlists.save(
        Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1),),
        )
    )
    repositories.libraries.save_default(
        MusicLibrary(
            id="default",
            root_path=Path("/Music/Library"),
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )


def _save_track(
    repositories: _Repositories,
    track_id: str,
    *,
    title: str,
    duration_seconds: int,
    status: LibraryTrackStatus = LibraryTrackStatus.ACTIVE,
) -> None:
    repositories.library_tracks.save(
        LibraryTrack(
            id=track_id,
            library_id="default",
            canonical_path=Path(f"/Music/Library/{track_id}.mp3"),
            filename=f"{track_id}.mp3",
            status=status,
            title=title,
            artist="Artist",
            duration_seconds=duration_seconds,
            normalized_title=title.casefold(),
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )


def _run_library_matching(repositories: _Repositories) -> RunLibraryMatching:
    return RunLibraryMatching(
        environments=repositories.environments,
        playlists=repositories.playlists,
        songs=repositories.songs,
        libraries=repositories.libraries,
        library_tracks=repositories.library_tracks,
        song_library_links=repositories.song_library_links,
    )


def _list_library_review(repositories: _Repositories) -> ListLibraryMatchReview:
    return ListLibraryMatchReview(
        environments=repositories.environments,
        playlists=repositories.playlists,
        songs=repositories.songs,
        libraries=repositories.libraries,
        library_tracks=repositories.library_tracks,
        song_library_links=repositories.song_library_links,
    )


def _manual_library_mapping(repositories: _Repositories) -> CreateManualLibraryMapping:
    return CreateManualLibraryMapping(
        environments=repositories.environments,
        playlists=repositories.playlists,
        songs=repositories.songs,
        libraries=repositories.libraries,
        library_tracks=repositories.library_tracks,
        song_library_links=repositories.song_library_links,
    )
