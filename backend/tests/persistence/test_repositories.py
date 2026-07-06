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
    LibraryAlignmentItem,
    LibraryAlignmentItemStatus,
    LibraryAlignmentRun,
    LibraryAlignmentRunStatus,
    LibraryMetadataAsset,
    LibraryMetadataAssetStatus,
    LibraryMetadataImportRun,
    LibraryMetadataImportRunStatus,
    LibraryMetadataIndexEntry,
    LibraryTrack,
    LibraryTrackStatus,
    MatchLink,
    MusicEnvironment,
    MusicLibrary,
    Playlist,
    PlaylistItem,
    RemotePlaylist,
    SongMaster,
    SongLibraryLink,
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
    SqliteLibraryAlignmentRunRepository,
    SqliteLibraryMetadataRepository,
    SqliteLibraryRepository,
    SqliteLibraryTrackRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteRemotePlaylistRepository,
    SqliteScanRunRepository,
    SqliteSongRepository,
    SqliteSongLibraryLinkRepository,
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
        size_bytes=123,
        modified_at=12.5,
        status=LibraryTrackStatus.ACTIVE,
        title="Track",
        artist="Artist",
        duration_seconds=180,
        normalized_title="track",
        file_hash=None,
        created_at="2026-07-06T10:00:00+00:00",
        updated_at="2026-07-06T10:00:00+00:00",
        first_seen_at="2026-07-06T10:00:00+00:00",
        last_seen_at="2026-07-06T10:00:00+00:00",
    )
    missing = LibraryTrack(
        id="library_track_2",
        library_id="default",
        canonical_path=Path("/Music/Library/missing.mp3"),
        filename="missing.mp3",
        status=LibraryTrackStatus.MISSING,
        normalized_title="track",
        duration_seconds=180,
        created_at="2026-07-06T10:00:00+00:00",
        updated_at="2026-07-06T11:00:00+00:00",
        missing_at="2026-07-06T11:00:00+00:00",
    )

    repository.save(track)
    repository.save(missing)

    assert repository.get("library_track_1") == track
    assert repository.get_by_canonical_path("default", track.canonical_path) == track
    assert repository.list("default") == [missing, track]
    assert repository.list_by_status("default", LibraryTrackStatus.ACTIVE) == [track]
    assert repository.count("default") == 1
    assert repository.count_by_status("default", LibraryTrackStatus.MISSING) == 1
    assert repository.get_by_identity("default", "track", 180) == [track]
    assert repository.get_by_identity("default", "track", 181) == []


def test_library_alignment_repository_round_trips_runs_and_items(
    sqlite_connection: sqlite3.Connection,
) -> None:
    SqliteEnvironmentRepository(sqlite_connection).save(
        MusicEnvironment(id="env_1", name="Gig USB", root_path=Path("/Volumes/GIG"))
    )
    SqliteLibraryRepository(sqlite_connection).save_default(
        MusicLibrary(
            id="default",
            root_path=Path("/Music/Library"),
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )
    track = LibraryTrack(
        id="library_track_1",
        library_id="default",
        canonical_path=Path("/Music/Library/track.mp3"),
        filename="track.mp3",
        created_at="2026-07-06T10:00:00+00:00",
        updated_at="2026-07-06T10:00:00+00:00",
    )
    SqliteLibraryTrackRepository(sqlite_connection).save(track)
    repository = SqliteLibraryAlignmentRunRepository(sqlite_connection)
    run = LibraryAlignmentRun(
        id="alignment_1",
        library_id="default",
        environment_id="env_1",
        status=LibraryAlignmentRunStatus.COMPLETED,
        started_at="2026-07-06T10:00:00+00:00",
        finished_at="2026-07-06T10:00:01+00:00",
        scanned_library_count=1,
        scanned_usb_count=1,
        copied_count=1,
    )
    item = LibraryAlignmentItem(
        id="alignment_item_1",
        run_id="alignment_1",
        status=LibraryAlignmentItemStatus.COPIED,
        source_path=Path("/Volumes/GIG/track.mp3"),
        target_path=Path("/Music/Library/track.mp3"),
        library_track_id="library_track_1",
        title="Track",
        duration_seconds=180,
        normalized_title="track",
    )

    repository.save(run, (item,))

    assert repository.get("alignment_1") == (run, (item,))
    assert repository.latest("default") == (run, (item,))


def test_library_metadata_repository_round_trips_runs_assets_and_latest_entries(
    sqlite_connection: sqlite3.Connection,
) -> None:
    SqliteEnvironmentRepository(sqlite_connection).save(
        MusicEnvironment(id="env_1", name="Gig USB", root_path=Path("/Volumes/GIG"))
    )
    SqliteLibraryRepository(sqlite_connection).save_default(
        MusicLibrary(
            id="default",
            root_path=Path("/Music/Library"),
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )
    repository = SqliteLibraryMetadataRepository(sqlite_connection)
    run = LibraryMetadataImportRun(
        id="metadata_run_1",
        library_id="default",
        environment_id="env_1",
        status=LibraryMetadataImportRunStatus.COMPLETED,
        started_at="2026-07-06T10:00:00+00:00",
        finished_at="2026-07-06T10:00:01+00:00",
        asset_count=1,
        index_entry_count=1,
    )
    asset = LibraryMetadataAsset(
        id="metadata_asset_1",
        run_id="metadata_run_1",
        library_id="default",
        provider="tracks_json",
        asset_type="tracks_json",
        source_path=Path("/Volumes/GIG/tracks.json"),
        stored_path=Path("/Music/Library/_music_manager/metadata-assets/metadata_run_1/tracks.json"),
        size_bytes=123,
        modified_at=12.5,
        imported_at="2026-07-06T10:00:00+00:00",
        status=LibraryMetadataAssetStatus.COPIED,
    )
    entry = LibraryMetadataIndexEntry(
        id="metadata_entry_1",
        library_id="default",
        provider="tracks_json",
        source_asset_id="metadata_asset_1",
        source_path=Path("/Volumes/GIG/tracks.json"),
        entry_key="id:track_1",
        payload_json='{"id":"track_1"}',
        imported_at="2026-07-06T10:00:00+00:00",
    )
    newer_entry = LibraryMetadataIndexEntry(
        id="metadata_entry_2",
        library_id="default",
        provider="tracks_json",
        source_asset_id="metadata_asset_1",
        source_path=Path("/Volumes/GIG/tracks.json"),
        entry_key="id:track_1",
        payload_json='{"id":"track_1","latest":true}',
        imported_at="2026-07-06T10:00:02+00:00",
    )

    repository.save_import_run(run, (asset,), (entry,))
    repository.save_import_run(run, (asset,), (newer_entry,))

    latest = repository.latest("default")
    assert latest is not None
    assert latest[0] == run
    assert latest[1] == (asset,)
    assert latest[2] == (newer_entry,)
    assert repository.count_assets("default") == 1
    assert repository.count_index_entries("default") == 1
    assert repository.last_imported_at("default") == "2026-07-06T10:00:01+00:00"


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


def test_song_library_link_repository_round_trips_and_replaces_links(
    sqlite_connection: sqlite3.Connection,
) -> None:
    SqliteSongRepository(sqlite_connection).save(SongMaster(id="song_1", title="Track"))
    SqliteLibraryRepository(sqlite_connection).save_default(
        MusicLibrary(
            id="default",
            root_path=Path("/Music/Library"),
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )
    track_repository = SqliteLibraryTrackRepository(sqlite_connection)
    for track_id in ("library_track_1", "library_track_2"):
        track_repository.save(
            LibraryTrack(
                id=track_id,
                library_id="default",
                canonical_path=Path(f"/Music/Library/{track_id}.mp3"),
                filename=f"{track_id}.mp3",
                status=LibraryTrackStatus.ACTIVE,
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )
    repository = SqliteSongLibraryLinkRepository(sqlite_connection)
    automatic = SongLibraryLink(
        song_id="song_1",
        library_track_id="library_track_1",
        method="library_identity_exact",
        confidence=1.0,
        created_at="2026-07-06T10:00:00+00:00",
        updated_at="2026-07-06T10:00:00+00:00",
    )
    manual = SongLibraryLink(
        song_id="song_1",
        library_track_id="library_track_2",
        method="manual",
        confidence=1.0,
        reviewed=True,
        created_at="2026-07-06T10:01:00+00:00",
        updated_at="2026-07-06T10:01:00+00:00",
    )

    repository.save(automatic)
    repository.delete_automatic_by_song("song_1")
    assert repository.list_by_song("song_1") == []

    repository.save(automatic)
    repository.replace_for_song(manual)

    assert repository.list_by_song("song_1") == [manual]
    assert repository.list_by_library_track("library_track_2") == [manual]


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
                action=ExportAction.WRITE_TRACKS_JSON,
                target_path=Path("/target/Playlist/tracks.json"),
                metadata_payload_json='[{"filename": "track.mp3"}]',
                reason="1 tracks.json entries; 0 tracks without metadata",
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
