import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest

from music_manager_backend.application.use_cases.import_soundcloud_playlist import (
    ImportSoundCloudPlaylist,
)
from music_manager_backend.domain.entities import MusicEnvironment, Playlist, SongMaster
from music_manager_backend.infrastructure.persistence import (
    SqliteEnvironmentRepository,
    SqlitePlaylistRepository,
    SqliteRemotePlaylistRepository,
    SqliteSongRepository,
    SqliteSyncSnapshotRepository,
)
from music_manager_backend.ports.soundcloud_models import (
    ParsedSoundCloudPlaylist,
    ParsedSoundCloudTrack,
)
from music_manager_backend.shared.errors import ValidationError

SOURCE_URL = "https://soundcloud.com/user/sets/funk"


@dataclass(frozen=True)
class Repositories:
    environments: SqliteEnvironmentRepository
    remote_playlists: SqliteRemotePlaylistRepository
    playlists: SqlitePlaylistRepository
    songs: SqliteSongRepository
    sync_snapshots: SqliteSyncSnapshotRepository


class FakeSoundCloudImporter:
    def __init__(self, playlists: list[ParsedSoundCloudPlaylist]) -> None:
        self.playlists = playlists
        self.urls: list[str] = []

    def import_playlist(self, url: str) -> ParsedSoundCloudPlaylist:
        self.urls.append(url)
        return self.playlists.pop(0)


def test_first_import_creates_durable_playlist_state(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    repositories.environments.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    importer = FakeSoundCloudImporter([_playlist((_track(1, "One", "artist/one"),))])

    result = _use_case(repositories, importer).execute("env_1", SOURCE_URL)

    assert importer.urls == [SOURCE_URL]
    assert result.playlist_name == "Funk"
    assert result.track_count == 1
    assert result.added == 1
    assert result.unchanged == 0
    remote_playlist = repositories.remote_playlists.get(result.remote_playlist_id)
    assert remote_playlist is not None
    assert remote_playlist.name == "Funk"
    playlist = repositories.playlists.get(result.playlist_id)
    assert playlist is not None
    assert playlist.items[0].remote_membership_active is True
    song = repositories.songs.get(playlist.items[0].song_id)
    assert song is not None
    assert song.source_url == "https://soundcloud.com/artist/one"
    snapshots = repositories.sync_snapshots.list_by_remote_playlist(result.remote_playlist_id)
    assert snapshots[0].payload["tracks"] == [
        {
            "position": 1,
            "title": "One",
            "uploader": "Artist",
            "uploader_url": "https://soundcloud.com/artist",
            "canonical_track_url": "https://soundcloud.com/artist/one",
            "playlist_track_url": "https://soundcloud.com/artist/one?in=user/sets/funk",
            "artwork_url": None,
            "play_count": None,
            "duration_seconds": None,
            "raw": {},
        }
    ]


def test_reimport_is_idempotent_for_entities(sqlite_connection: sqlite3.Connection) -> None:
    repositories = _repositories(sqlite_connection)
    repositories.environments.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    importer = FakeSoundCloudImporter(
        [
            _playlist((_track(1, "One", "artist/one"),)),
            _playlist((_track(1, "One", "artist/one"),)),
        ]
    )
    use_case = _use_case(repositories, importer)

    first = use_case.execute("env_1", SOURCE_URL)
    second = use_case.execute("env_1", SOURCE_URL)

    assert second.remote_playlist_id == first.remote_playlist_id
    assert second.playlist_id == first.playlist_id
    assert second.added == 0
    assert second.removed == 0
    assert second.unchanged == 1
    assert len(repositories.playlists.list_by_environment("env_1")) == 1


def test_import_detects_added_removed_reactivated_reordered_and_metadata_changes(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    repositories.environments.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    importer = FakeSoundCloudImporter(
        [
            _playlist(
                (
                    _track(1, "One", "artist/one"),
                    _track(2, "Two", "artist/two"),
                )
            ),
            _playlist(
                (
                    _track(1, "Two Updated", "artist/two"),
                    _track(2, "Three", "artist/three"),
                )
            ),
            _playlist(
                (
                    _track(1, "One", "artist/one"),
                    _track(2, "Two Updated", "artist/two"),
                    _track(3, "Three", "artist/three"),
                )
            ),
        ]
    )
    use_case = _use_case(repositories, importer)

    use_case.execute("env_1", SOURCE_URL)
    second = use_case.execute("env_1", SOURCE_URL)
    third = use_case.execute("env_1", SOURCE_URL)

    assert second.added == 1
    assert second.removed == 1
    assert second.reactivated == 0
    assert second.reordered == 1
    assert second.metadata_changed == 1
    assert third.reactivated == 1
    assert third.reordered == 2
    assert third.unchanged == 0


def test_import_preserves_local_overrides(sqlite_connection: sqlite3.Connection) -> None:
    repositories = _repositories(sqlite_connection)
    repositories.environments.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    importer = FakeSoundCloudImporter(
        [
            _playlist((_track(1, "One", "artist/one"),)),
            _playlist((_track(1, "One Remote Changed", "artist/one"),)),
        ]
    )
    use_case = _use_case(repositories, importer)
    first = use_case.execute("env_1", SOURCE_URL)
    playlist = repositories.playlists.get(first.playlist_id)
    assert playlist is not None
    repositories.playlists.save(
        Playlist(
            id=playlist.id,
            environment_id=playlist.environment_id,
            name=playlist.name,
            remote_playlist_id=playlist.remote_playlist_id,
            local_name_override="Local Playlist",
            items=playlist.items,
        )
    )
    song_id = playlist.items[0].song_id
    song = repositories.songs.get(song_id)
    assert song is not None
    repositories.songs.save(
        SongMaster(
            id=song.id,
            title=song.title,
            artist=song.artist,
            duration_seconds=song.duration_seconds,
            source_track_id=song.source_track_id,
            source_url=song.source_url,
            local_title_override="Local Song",
            local_artist_override="Local Artist",
        )
    )

    second = use_case.execute("env_1", SOURCE_URL)

    updated_playlist = repositories.playlists.get(second.playlist_id)
    updated_song = repositories.songs.get(song_id)
    assert updated_playlist is not None
    assert updated_song is not None
    assert second.playlist_name == "Local Playlist"
    assert updated_playlist.local_name_override == "Local Playlist"
    assert updated_song.title == "One Remote Changed"
    assert updated_song.local_title_override == "Local Song"
    assert updated_song.local_artist_override == "Local Artist"


def test_different_canonical_urls_are_not_merged(sqlite_connection: sqlite3.Connection) -> None:
    repositories = _repositories(sqlite_connection)
    repositories.environments.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    importer = FakeSoundCloudImporter(
        [
            _playlist(
                (
                    _track(1, "Same Title", "artist/mix-a"),
                    _track(2, "Same Title", "artist/mix-b"),
                )
            )
        ]
    )

    result = _use_case(repositories, importer).execute("env_1", SOURCE_URL)

    playlist = repositories.playlists.get(result.playlist_id)
    assert playlist is not None
    assert len({item.song_id for item in playlist.items}) == 2


def test_zero_track_import_raises_validation_error(sqlite_connection: sqlite3.Connection) -> None:
    repositories = _repositories(sqlite_connection)
    repositories.environments.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    importer = FakeSoundCloudImporter([_playlist(())])

    with pytest.raises(ValidationError) as error:
        _use_case(repositories, importer).execute("env_1", SOURCE_URL)

    assert error.value.code == "soundcloud_playlist_no_tracks"
    assert "make it public" in error.value.message
    assert repositories.remote_playlists.get_by_source_url("soundcloud", SOURCE_URL) is None


def _repositories(sqlite_connection: sqlite3.Connection) -> Repositories:
    return Repositories(
        environments=SqliteEnvironmentRepository(sqlite_connection),
        remote_playlists=SqliteRemotePlaylistRepository(sqlite_connection),
        playlists=SqlitePlaylistRepository(sqlite_connection),
        songs=SqliteSongRepository(sqlite_connection),
        sync_snapshots=SqliteSyncSnapshotRepository(sqlite_connection),
    )


def _use_case(
    repositories: Repositories, importer: FakeSoundCloudImporter
) -> ImportSoundCloudPlaylist:
    return ImportSoundCloudPlaylist(
        environments=repositories.environments,
        remote_playlists=repositories.remote_playlists,
        playlists=repositories.playlists,
        songs=repositories.songs,
        sync_snapshots=repositories.sync_snapshots,
        importer=importer,
    )


def _playlist(
    tracks: tuple[ParsedSoundCloudTrack, ...],
    warnings: tuple[str, ...] = (),
) -> ParsedSoundCloudPlaylist:
    return ParsedSoundCloudPlaylist(
        source_url=SOURCE_URL,
        title="Funk",
        tracks=tracks,
        warnings=warnings,
    )


def _track(position: int, title: str, path: str) -> ParsedSoundCloudTrack:
    artist = path.split("/", maxsplit=1)[0].title()
    return ParsedSoundCloudTrack(
        position=position,
        title=title,
        uploader=artist,
        uploader_url=f"https://soundcloud.com/{path.split('/', maxsplit=1)[0]}",
        canonical_track_url=f"https://soundcloud.com/{path}",
        playlist_track_url=f"https://soundcloud.com/{path}?in=user/sets/funk",
    )
