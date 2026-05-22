import sqlite3
from pathlib import Path

from music_manager_backend.domain.entities import (
    AudioFile,
    ExportPlan,
    ExportPlanItem,
    MatchLink,
    MusicEnvironment,
    Playlist,
    PlaylistItem,
    RemotePlaylist,
    SongMaster,
    SyncSnapshot,
)
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteExportPlanRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteRemotePlaylistRepository,
    SqliteSongRepository,
    SqliteSyncSnapshotRepository,
)


def test_environment_repository_round_trips_paths(sqlite_connection: sqlite3.Connection) -> None:
    repository = SqliteEnvironmentRepository(sqlite_connection)
    environment = MusicEnvironment(id="env_1", name="Gig USB", root_path=Path("/Volumes/GIG"))

    repository.save(environment)

    assert repository.get("env_1") == environment
    assert repository.list() == [environment]


def test_song_repository_preserves_local_overrides(sqlite_connection: sqlite3.Connection) -> None:
    repository = SqliteSongRepository(sqlite_connection)
    song = SongMaster(
        id="song_1",
        title="Remote Title",
        artist="Remote Artist",
        duration_seconds=320,
        source_track_id="sc_1",
        source_url="https://soundcloud.example/track",
        local_title_override="Local Title",
        local_artist_override="Local Artist",
    )

    repository.save(song)

    assert repository.get("song_1") == song


def test_playlist_repository_preserves_items_and_overrides(
    sqlite_connection: sqlite3.Connection,
) -> None:
    _save_environment(sqlite_connection)
    remote_playlist = RemotePlaylist(
        id="remote_1",
        source="soundcloud",
        source_url="https://soundcloud.example/playlist",
        name="Remote",
    )
    SqliteRemotePlaylistRepository(sqlite_connection).save(remote_playlist)
    SqliteSongRepository(sqlite_connection).save(SongMaster(id="song_1", title="Track"))
    repository = SqlitePlaylistRepository(sqlite_connection)
    playlist = Playlist(
        id="playlist_1",
        environment_id="env_1",
        name="Remote Name",
        remote_playlist_id="remote_1",
        local_name_override="Local Name",
        items=(PlaylistItem(song_id="song_1", position=1, remote_membership_active=False),),
    )

    repository.save(playlist)

    assert repository.get("playlist_1") == playlist
    assert repository.list_by_environment("env_1") == [playlist]


def test_audio_file_repository_round_trips_metadata(sqlite_connection: sqlite3.Connection) -> None:
    _save_environment(sqlite_connection)
    repository = SqliteAudioFileRepository(sqlite_connection)
    audio_file = AudioFile(
        id="file_1",
        environment_id="env_1",
        path=Path("/Volumes/GIG/track.mp3"),
        size_bytes=123,
        modified_at=12.5,
        title="Track",
        artist="Artist",
        duration_seconds=300,
    )

    repository.save(audio_file)

    assert repository.get("file_1") == audio_file
    assert repository.list_by_environment("env_1") == [audio_file]


def test_match_repository_preserves_manual_review_flags(
    sqlite_connection: sqlite3.Connection,
) -> None:
    _save_environment(sqlite_connection)
    SqliteSongRepository(sqlite_connection).save(SongMaster(id="song_1", title="Track"))
    SqliteAudioFileRepository(sqlite_connection).save(
        AudioFile(
            id="file_1",
            environment_id="env_1",
            path=Path("/Volumes/GIG/track.mp3"),
            size_bytes=123,
            modified_at=12.5,
        )
    )
    repository = SqliteMatchLinkRepository(sqlite_connection)
    match = MatchLink(
        song_id="song_1",
        audio_file_id="file_1",
        method="manual",
        confidence=1.0,
        reviewed=True,
    )

    repository.save(match)

    assert repository.list_by_song("song_1") == [match]


def test_sync_snapshot_repository_round_trips_json_payload(
    sqlite_connection: sqlite3.Connection,
) -> None:
    remote_playlist = RemotePlaylist(
        id="remote_1",
        source="soundcloud",
        source_url="https://soundcloud.example/playlist",
        name="Remote",
    )
    SqliteRemotePlaylistRepository(sqlite_connection).save(remote_playlist)
    repository = SqliteSyncSnapshotRepository(sqlite_connection)
    snapshot = SyncSnapshot(
        id="snapshot_1",
        source="soundcloud",
        remote_playlist_id="remote_1",
        captured_at="2026-05-22T10:00:00+00:00",
        payload={"tracks": [{"id": "track_1"}]},
    )

    repository.save(snapshot)

    assert repository.list_by_remote_playlist("remote_1") == [snapshot]


def test_export_plan_repository_round_trips_items(sqlite_connection: sqlite3.Connection) -> None:
    _save_environment(sqlite_connection)
    repository = SqliteExportPlanRepository(sqlite_connection)
    plan = ExportPlan(
        id="plan_1",
        environment_id="env_1",
        items=(
            ExportPlanItem(
                action=ExportAction.COPY_FILE,
                source_path=Path("/source/track.mp3"),
                target_path=Path("/target/Playlist/track.mp3"),
            ),
            ExportPlanItem(
                action=ExportAction.SKIP,
                target_path=Path("/target/Missing.mp3"),
                reason="missing audio",
            ),
        ),
    )

    repository.save(plan)

    assert repository.get("plan_1") == plan


def _save_environment(connection: sqlite3.Connection) -> None:
    SqliteEnvironmentRepository(connection).save(
        MusicEnvironment(id="env_1", name="Gig USB", root_path=Path("/Volumes/GIG"))
    )
