import sqlite3
from pathlib import Path

from music_manager_backend.application.use_cases.plan_export import PlanExport
from music_manager_backend.domain.entities import (
    AudioFile,
    MatchLink,
    MusicEnvironment,
    Playlist,
    PlaylistItem,
    SongMaster,
)
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.infrastructure.filesystem import update_export_manifest
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteExportPlanRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteSongRepository,
)


def test_export_plan_creates_folders_and_copy_items(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "source.mp3")
    repositories.songs.save(SongMaster(id="song_1", title="Track", artist="Artist"))
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="metadata_exact",
            confidence=0.95,
        )
    )

    plan = _plan_export(repositories).execute("env_1")

    assert [item.action for item in plan.items].count(ExportAction.CREATE_FOLDER) == 3
    copy_items = [item for item in plan.items if item.action == ExportAction.COPY_FILE]
    assert copy_items[0].source_path == source
    assert copy_items[0].target_path == root / "Set" / "source.mp3"
    assert not (root / ".music_manager").exists()
    assert not (root / "Set").exists()


def test_export_plan_duplicates_shared_songs_per_playlist(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "shared.mp3")
    repositories.songs.save(SongMaster(id="song_1", title="Shared", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="A",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_2",
            environment_id="env_1",
            name="B",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    copy_targets = [
        item.target_path
        for item in plan.items
        if item.action == ExportAction.COPY_FILE
    ]
    assert copy_targets == [
        root / "A" / "shared.mp3",
        root / "B" / "shared.mp3",
    ]


def test_export_plan_keeps_file_already_in_playlist_folder(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = root / "Set" / "already-there.mp3"
    source.parent.mkdir()
    source.write_bytes(b"audio")
    repositories.songs.save(SongMaster(id="song_1", title="Track", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="metadata_exact",
            confidence=0.95,
        )
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    keep_items = [item for item in plan.items if item.action == ExportAction.KEEP_EXISTING]
    assert keep_items[0].source_path == source
    assert keep_items[0].target_path == source
    assert not [item for item in plan.items if item.action == ExportAction.COPY_FILE]
    assert not [
        item
        for item in plan.items
        if item.action == ExportAction.REMOVE_STALE_COPY and item.target_path == source
    ]


def test_export_plan_prefers_linked_copy_in_target_playlist_folder(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    generic_source = _source_file(root, "bongoloco.mp3")
    folder_source = root / "03_HOUSE" / "bongoloco.mp3"
    folder_source.parent.mkdir()
    folder_source.write_bytes(b"audio")
    repositories.songs.save(SongMaster(id="song_1", title="Bongoloco", artist="Bruno Furlan"))
    repositories.audio_files.save(_audio_file("file_generic", generic_source))
    repositories.audio_files.save(_audio_file("file_house", folder_source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_generic",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_house",
            method="local_duplicate",
            confidence=0.99,
            reviewed=True,
        )
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="03_HOUSE",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    keep_items = [item for item in plan.items if item.action == ExportAction.KEEP_EXISTING]
    assert keep_items[0].source_path == folder_source
    assert keep_items[0].target_path == folder_source
    assert not [item for item in plan.items if item.action == ExportAction.COPY_FILE]


def test_export_plan_omits_existing_folders(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    (root / ".music_manager" / "_deprecated").mkdir(parents=True)
    (root / "Set").mkdir()
    source = _source_file(root, "source.mp3")
    repositories.songs.save(SongMaster(id="song_1", title="Track", artist="Artist"))
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="metadata_exact",
            confidence=0.95,
        )
    )

    plan = _plan_export(repositories).execute("env_1")

    assert not [item for item in plan.items if item.action == ExportAction.CREATE_FOLDER]


def test_export_plan_skips_missing_and_ambiguous_tracks(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    candidate = _source_file(root, "candidate.mp3")
    repositories.songs.save(SongMaster(id="song_1", title="Missing", artist="Artist"))
    repositories.songs.save(SongMaster(id="song_2", title="Candidate"))
    repositories.audio_files.save(_audio_file("file_1", candidate, title="Candidate"))
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(
                PlaylistItem(song_id="song_1", position=1),
                PlaylistItem(song_id="song_2", position=2),
            ),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    skip_items = [item for item in plan.items if item.action == ExportAction.SKIP]
    assert len(skip_items) == 2
    assert {item.reason for item in skip_items} == {
        "No accepted audio file for Candidate",
        "No accepted audio file for Missing",
    }
    assert not [item for item in plan.items if item.action == ExportAction.COPY_FILE]


def test_export_plan_skips_likely_preview_matches(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "preview.mp3")
    repositories.songs.save(SongMaster(id="song_1", title="Preview", artist="Artist"))
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )
    repositories.audio_files.save(_audio_file("file_1", source, duration_seconds=37))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )

    plan = _plan_export(repositories).execute("env_1")

    assert not [item for item in plan.items if item.action == ExportAction.COPY_FILE]
    skip_items = [item for item in plan.items if item.action == ExportAction.SKIP]
    assert skip_items[0].reason == (
        "Matched audio file is likely a preview download under 60 seconds"
    )


def test_export_plan_detects_stale_files(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    stale = root / "Set" / "stale.mp3"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")
    update_export_manifest(root_path=root, add_targets={stale}, remove_targets=set())
    _seed_playlist(
        repositories,
        playlist=Playlist(id="playlist_1", environment_id="env_1", name="Set"),
    )

    plan = _plan_export(repositories).execute("env_1")

    assert any(
        item.action == ExportAction.REMOVE_STALE_COPY and item.target_path == stale
        for item in plan.items
    )


def test_export_plan_existing_target_is_not_reported_or_removed_as_stale(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "source.mp3")
    target = root / "Set" / "source.mp3"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing")
    update_export_manifest(root_path=root, add_targets={target}, remove_targets=set())
    repositories.songs.save(SongMaster(id="song_1", title="Track", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="metadata_exact",
            confidence=0.95,
        )
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    keep_items = [item for item in plan.items if item.action == ExportAction.KEEP_EXISTING]
    assert keep_items[0].source_path == source
    assert keep_items[0].target_path == target
    assert not [item for item in plan.items if item.action == ExportAction.COPY_FILE]
    assert not [
        item
        for item in plan.items
        if item.action == ExportAction.REMOVE_STALE_COPY and item.target_path == target
    ]


def test_export_plan_does_not_mark_unowned_root_files_as_stale(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    user_file = root / "Set" / "user-file.mp3"
    user_file.parent.mkdir(parents=True)
    user_file.write_bytes(b"user audio")
    _seed_playlist(
        repositories,
        playlist=Playlist(id="playlist_1", environment_id="env_1", name="Set"),
    )

    plan = _plan_export(repositories).execute("env_1")

    assert not any(
        item.action == ExportAction.REMOVE_STALE_COPY and item.target_path == user_file
        for item in plan.items
    )


def test_export_plan_preserves_deprecated_matched_songs(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "old.mp3")
    repositories.songs.save(SongMaster(id="song_1", title="Old", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1, remote_membership_active=False),),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    deprecated = [item for item in plan.items if item.action == ExportAction.PRESERVE_DEPRECATED]
    assert deprecated[0].source_path == source
    assert deprecated[0].target_path == root / ".music_manager" / "_deprecated" / "old.mp3"


def test_export_plan_preserves_removed_song_before_removing_stale_playlist_copy(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = root / "Set" / "old.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"old audio")
    update_export_manifest(root_path=root, add_targets={source}, remove_targets=set())
    repositories.songs.save(SongMaster(id="song_1", title="Old", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1, remote_membership_active=False),),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    preserve = next(item for item in plan.items if item.action == ExportAction.PRESERVE_DEPRECATED)
    remove = next(item for item in plan.items if item.action == ExportAction.REMOVE_STALE_COPY)
    assert plan.items.index(preserve) < plan.items.index(remove)
    assert preserve.source_path == source
    assert preserve.target_path == root / ".music_manager" / "_deprecated" / "old.mp3"
    assert remove.target_path == source


def test_export_plan_copies_active_elsewhere_before_removing_stale_playlist_copy(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = root / "Old Set" / "shared.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"shared audio")
    update_export_manifest(root_path=root, add_targets={source}, remove_targets=set())
    repositories.songs.save(SongMaster(id="song_1", title="Shared", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Old Set",
            items=(PlaylistItem(song_id="song_1", position=1, remote_membership_active=False),),
        ),
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_2",
            environment_id="env_1",
            name="Current Set",
            items=(PlaylistItem(song_id="song_1", position=1),),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    copy = next(item for item in plan.items if item.action == ExportAction.COPY_FILE)
    remove = next(item for item in plan.items if item.action == ExportAction.REMOVE_STALE_COPY)
    assert not [item for item in plan.items if item.action == ExportAction.PRESERVE_DEPRECATED]
    assert plan.items.index(copy) < plan.items.index(remove)
    assert copy.source_path == source
    assert copy.target_path == root / "Current Set" / "shared.mp3"
    assert remove.target_path == source


def test_export_plan_keeps_existing_deprecated_backup(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "old.mp3")
    backup = root / ".music_manager" / "_deprecated" / "old.mp3"
    backup.parent.mkdir(parents=True)
    backup.write_bytes(b"backup")
    repositories.songs.save(SongMaster(id="song_1", title="Old", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )
    _seed_playlist(
        repositories,
        playlist=Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(PlaylistItem(song_id="song_1", position=1, remote_membership_active=False),),
        ),
    )

    plan = _plan_export(repositories).execute("env_1")

    assert not [item for item in plan.items if item.action == ExportAction.KEEP_EXISTING]
    assert not [
        item
        for item in plan.items
        if item.action == ExportAction.PRESERVE_DEPRECATED and item.target_path == backup
    ]


class _Repositories:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.environments = SqliteEnvironmentRepository(connection)
        self.playlists = SqlitePlaylistRepository(connection)
        self.songs = SqliteSongRepository(connection)
        self.audio_files = SqliteAudioFileRepository(connection)
        self.match_links = SqliteMatchLinkRepository(connection)
        self.export_plans = SqliteExportPlanRepository(connection)


def _repositories(connection: sqlite3.Connection) -> _Repositories:
    return _Repositories(connection)


def _seed_environment(repositories: _Repositories, tmp_path: Path) -> Path:
    root = tmp_path / "usb"
    root.mkdir()
    repositories.environments.save(MusicEnvironment(id="env_1", name="USB", root_path=root))
    return root


def _seed_playlist(repositories: _Repositories, *, playlist: Playlist) -> None:
    repositories.playlists.save(playlist)


def _source_file(root: Path, filename: str) -> Path:
    source = root / "source" / filename
    source.parent.mkdir(exist_ok=True)
    source.write_bytes(b"audio")
    return source


def _audio_file(
    audio_file_id: str,
    path: Path,
    *,
    title: str | None = None,
    duration_seconds: int | None = None,
) -> AudioFile:
    return AudioFile(
        id=audio_file_id,
        environment_id="env_1",
        path=path,
        size_bytes=1,
        modified_at=1.0,
        title=title,
        duration_seconds=duration_seconds,
    )


def _plan_export(repositories: _Repositories) -> PlanExport:
    return PlanExport(
        environments=repositories.environments,
        playlists=repositories.playlists,
        songs=repositories.songs,
        audio_files=repositories.audio_files,
        match_links=repositories.match_links,
        export_plans=repositories.export_plans,
    )
