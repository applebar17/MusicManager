import sqlite3
from pathlib import Path

from music_manager_backend.domain.entities import (
    AudioFile,
    ExportApplyItemResult,
    ExportApplyItemStatus,
    ExportApplyRun,
    ExportApplyRunStatus,
    ExportPlan,
    ExportPlanItem,
    LibraryTrack,
    MatchLink,
    MusicEnvironment,
    MusicLibrary,
    Playlist,
    PlaylistItem,
    RemotePlaylist,
    SongMaster,
    SyncSnapshot,
)
from music_manager_backend.domain.entities.audio_file import AudioFileStatus
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.domain.entities.scan_run import ScanRun
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteExportApplyRunRepository,
    SqliteExportPlanRepository,
    SqliteLibraryRepository,
    SqliteLibraryTrackRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteRemotePlaylistRepository,
    SqliteScanRunRepository,
    SqliteSongRepository,
    SqliteSyncSnapshotRepository,
)


def test_environment_repository_round_trips_paths(sqlite_connection: sqlite3.Connection) -> None:
    repository = SqliteEnvironmentRepository(sqlite_connection)
    environment = MusicEnvironment(id="env_1", name="Gig USB", root_path=Path("/Volumes/GIG"))

    repository.save(environment)

    assert repository.get("env_1") == environment
    assert repository.list() == [environment]


def test_environment_repository_soft_archives(sqlite_connection: sqlite3.Connection) -> None:
    repository = SqliteEnvironmentRepository(sqlite_connection)
    environment = MusicEnvironment(id="env_1", name="Gig USB", root_path=Path("/Volumes/GIG"))
    repository.save(environment)

    archived = repository.archive("env_1", "2026-05-22T10:00:00+00:00")

    assert archived is not None
    assert archived.archived_at == "2026-05-22T10:00:00+00:00"
    assert repository.list() == []
    assert repository.list(include_archived=True) == [archived]


def test_library_repository_round_trips_singleton_config(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repository = SqliteLibraryRepository(sqlite_connection)
    library = MusicLibrary(
        id="default",
        root_path=Path("/Music/Library"),
        created_at="2026-07-06T10:00:00+00:00",
        updated_at="2026-07-06T10:00:00+00:00",
    )
    updated = MusicLibrary(
        id="default",
        root_path=Path("/Music/Updated"),
        created_at="2026-07-06T10:00:00+00:00",
        updated_at="2026-07-06T11:00:00+00:00",
    )

    repository.save_default(library)
    repository.save_default(updated)

    assert repository.get_default() == updated


def test_library_track_repository_round_trips_tracks_and_identity(
    sqlite_connection: sqlite3.Connection,
) -> None:
    SqliteLibraryRepository(sqlite_connection).save_default(
        MusicLibrary(
            id="default",
            root_path=Path("/Music/Library"),
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )
    repository = SqliteLibraryTrackRepository(sqlite_connection)
    track = LibraryTrack(
        id="library_track_1",
        library_id="default",
        canonical_path=Path("/Music/Library/track.mp3"),
        filename="track.mp3",
        title="Track",
        artist="Artist",
        duration_seconds=180,
        normalized_title="track",
        file_hash=None,
        created_at="2026-07-06T10:00:00+00:00",
        updated_at="2026-07-06T10:00:00+00:00",
    )

    repository.save(track)

    assert repository.get("library_track_1") == track
    assert repository.list("default") == [track]
    assert repository.count("default") == 1
    assert repository.get_by_identity("default", "track", 180) == [track]
    assert repository.get_by_identity("default", "track", 181) == []


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
    assert repository.get_by_source_url("https://soundcloud.example/track") == song


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
    assert repository.get_by_environment_remote_playlist("env_1", "remote_1") == playlist


def test_remote_playlist_repository_gets_by_source_url(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repository = SqliteRemotePlaylistRepository(sqlite_connection)
    remote_playlist = RemotePlaylist(
        id="remote_1",
        source="soundcloud",
        source_url="https://soundcloud.example/playlist",
        name="Remote",
    )

    repository.save(remote_playlist)

    assert repository.get_by_source_url(
        "soundcloud", "https://soundcloud.example/playlist"
    ) == remote_playlist


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
        album="Album",
        duration_seconds=300,
        bpm=128,
        key="9A",
        comment="Peak",
        raw_metadata={"title": "Track", "bpm": 128},
    )

    repository.save(audio_file)

    assert repository.get("file_1") == audio_file
    assert repository.list_by_environment("env_1") == [audio_file]
    assert repository.list_by_environment("env_1", status=AudioFileStatus.ACTIVE) == [audio_file]


def test_audio_file_repository_lists_unmanaged_active_files(
    sqlite_connection: sqlite3.Connection,
) -> None:
    _save_environment(sqlite_connection)
    SqliteSongRepository(sqlite_connection).save(SongMaster(id="song_1", title="Track"))
    audio_repository = SqliteAudioFileRepository(sqlite_connection)
    matched = AudioFile(
        id="file_1",
        environment_id="env_1",
        path=Path("/Volumes/GIG/matched.mp3"),
        size_bytes=123,
        modified_at=12.5,
    )
    unmanaged = AudioFile(
        id="file_2",
        environment_id="env_1",
        path=Path("/Volumes/GIG/unmanaged.mp3"),
        size_bytes=456,
        modified_at=13.5,
    )
    audio_repository.save(matched)
    audio_repository.save(unmanaged)
    SqliteMatchLinkRepository(sqlite_connection).save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="manual",
            confidence=1.0,
        )
    )

    assert audio_repository.list_unmanaged_active_by_environment("env_1") == [unmanaged]


def test_scan_run_repository_round_trips_summary(sqlite_connection: sqlite3.Connection) -> None:
    _save_environment(sqlite_connection)
    repository = SqliteScanRunRepository(sqlite_connection)
    scan_run = ScanRun(
        id="scan_1",
        environment_id="env_1",
        started_at="2026-05-22T10:00:00+00:00",
        finished_at="2026-05-22T10:00:01+00:00",
        added_count=1,
        changed_count=2,
        removed_count=3,
        moved_count=4,
        unchanged_count=5,
        total_active_count=6,
    )

    repository.save(scan_run)

    assert repository.get("scan_1") == scan_run


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


def test_match_repository_replaces_links_for_song(
    sqlite_connection: sqlite3.Connection,
) -> None:
    _save_environment(sqlite_connection)
    SqliteSongRepository(sqlite_connection).save(SongMaster(id="song_1", title="Track"))
    audio_repository = SqliteAudioFileRepository(sqlite_connection)
    audio_repository.save(
        AudioFile(
            id="file_1",
            environment_id="env_1",
            path=Path("/Volumes/GIG/track-1.mp3"),
            size_bytes=123,
            modified_at=12.5,
        )
    )
    audio_repository.save(
        AudioFile(
            id="file_2",
            environment_id="env_1",
            path=Path("/Volumes/GIG/track-2.mp3"),
            size_bytes=123,
            modified_at=12.5,
        )
    )
    repository = SqliteMatchLinkRepository(sqlite_connection)
    repository.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="metadata_exact",
            confidence=0.95,
        )
    )

    replacement = MatchLink(
        song_id="song_1",
        audio_file_id="file_2",
        method="manual",
        confidence=1.0,
        reviewed=True,
    )
    repository.replace_for_song(replacement)

    assert repository.list_by_song("song_1") == [replacement]


def test_match_repository_deletes_automatic_links_only(
    sqlite_connection: sqlite3.Connection,
) -> None:
    _save_environment(sqlite_connection)
    SqliteSongRepository(sqlite_connection).save(SongMaster(id="song_1", title="Track"))
    audio_repository = SqliteAudioFileRepository(sqlite_connection)
    for audio_file_id in ("file_1", "file_2"):
        audio_repository.save(
            AudioFile(
                id=audio_file_id,
                environment_id="env_1",
                path=Path(f"/Volumes/GIG/{audio_file_id}.mp3"),
                size_bytes=123,
                modified_at=12.5,
            )
        )
    repository = SqliteMatchLinkRepository(sqlite_connection)
    manual = MatchLink(
        song_id="song_1",
        audio_file_id="file_1",
        method="manual",
        confidence=1.0,
        reviewed=True,
    )
    repository.save(manual)
    repository.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_2",
            method="metadata_exact",
            confidence=0.95,
        )
    )

    repository.delete_automatic_by_song("song_1")

    assert repository.list_by_song("song_1") == [manual]


def test_match_repository_deletes_links_by_audio_file(
    sqlite_connection: sqlite3.Connection,
) -> None:
    _save_environment(sqlite_connection)
    SqliteSongRepository(sqlite_connection).save(SongMaster(id="song_1", title="Track"))
    SqliteSongRepository(sqlite_connection).save(SongMaster(id="song_2", title="Track 2"))
    audio_repository = SqliteAudioFileRepository(sqlite_connection)
    audio_repository.save(
        AudioFile(
            id="file_1",
            environment_id="env_1",
            path=Path("/Volumes/GIG/file_1.mp3"),
            size_bytes=123,
            modified_at=12.5,
        )
    )
    repository = SqliteMatchLinkRepository(sqlite_connection)
    repository.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )
    repository.save(
        MatchLink(
            song_id="song_2",
            audio_file_id="file_1",
            method="metadata_exact",
            confidence=0.95,
        )
    )

    repository.delete_by_audio_file("file_1")

    assert repository.list_by_song("song_1") == []
    assert repository.list_by_song("song_2") == []


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
                action=ExportAction.CREATE_FOLDER,
                target_path=Path("/target/Playlist"),
            ),
            ExportPlanItem(
                action=ExportAction.COPY_FILE,
                source_path=Path("/source/track.mp3"),
                target_path=Path("/target/Playlist/track.mp3"),
            ),
            ExportPlanItem(
                action=ExportAction.KEEP_EXISTING,
                source_path=Path("/source/already.mp3"),
                target_path=Path("/target/Playlist/already.mp3"),
                reason="matched audio is already in this playlist folder",
            ),
            ExportPlanItem(
                action=ExportAction.REMOVE_STALE_COPY,
                target_path=Path("/target/Playlist/stale.mp3"),
                reason="stale app-owned export copy",
            ),
            ExportPlanItem(
                action=ExportAction.PRESERVE_DEPRECATED,
                source_path=Path("/source/old.mp3"),
                target_path=Path("/target/_deprecated/old.mp3"),
                reason="song no longer belongs to any active playlist",
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


def test_export_apply_run_repository_round_trips_results(
    sqlite_connection: sqlite3.Connection,
) -> None:
    _save_environment(sqlite_connection)
    SqliteExportPlanRepository(sqlite_connection).save(
        ExportPlan(id="plan_1", environment_id="env_1")
    )
    repository = SqliteExportApplyRunRepository(sqlite_connection)
    apply_run = ExportApplyRun(
        id="apply_1",
        export_plan_id="plan_1",
        environment_id="env_1",
        status=ExportApplyRunStatus.COMPLETED_WITH_FAILURES,
        started_at="2026-05-22T10:00:00+00:00",
        finished_at="2026-05-22T10:00:01+00:00",
        item_results=(
            ExportApplyItemResult(
                action=ExportAction.COPY_FILE,
                source_path=Path("/source/track.mp3"),
                target_path=Path("/target/track.mp3"),
                status=ExportApplyItemStatus.SUCCEEDED,
                created_at="2026-05-22T10:00:00+00:00",
            ),
            ExportApplyItemResult(
                action=ExportAction.SKIP,
                target_path=Path("/target/missing.mp3"),
                status=ExportApplyItemStatus.SKIPPED,
                error_code="skipped",
                error_message="missing audio",
                created_at="2026-05-22T10:00:01+00:00",
            ),
        ),
    )

    repository.save(apply_run)

    assert repository.get("apply_1") == apply_run


def _save_environment(connection: sqlite3.Connection) -> None:
    SqliteEnvironmentRepository(connection).save(
        MusicEnvironment(id="env_1", name="Gig USB", root_path=Path("/Volumes/GIG"))
    )
