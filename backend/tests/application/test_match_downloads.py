import sqlite3
from pathlib import Path

from music_manager_backend.application.use_cases.match_downloads import MatchDownloads
from music_manager_backend.domain.entities import (
    AudioFile,
    AudioMetadata,
    MatchLink,
    MusicEnvironment,
    Playlist,
    PlaylistItem,
    SongMaster,
)
from music_manager_backend.infrastructure.filesystem import LocalAudioScanner
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteScanRunRepository,
    SqliteSongRepository,
)


def test_match_downloads_scans_and_matches_download_file(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root, downloads = _seed_environment(repositories, tmp_path)
    downloaded = downloads / "track.mp3"
    downloaded.write_bytes(b"audio")
    _seed_song_playlist(repositories, SongMaster(id="song_1", title="Track", artist="Artist"))
    metadata_reader = FakeMetadataReader(
        {downloaded: AudioMetadata(title="Track", artist="Artist", duration_seconds=180)}
    )

    result = _match_downloads(repositories, metadata_reader).execute("env_1")

    assert result.download_path == str(downloads)
    assert result.scan.added == 1
    assert result.matching.matched == 1
    audio_file = repositories.audio_files.list_by_environment("env_1")[0]
    assert audio_file.path == downloaded
    assert repositories.match_links.list_by_song("song_1") == [
        MatchLink(
            song_id="song_1",
            audio_file_id=audio_file.id,
            method="metadata_exact",
            confidence=0.95,
        )
    ]
    assert not (root / "Set" / "track.mp3").exists()


def test_match_downloads_preserves_reviewed_and_unrelated_automatic_links(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root, downloads = _seed_environment(repositories, tmp_path)
    manual_source = root / "manual.mp3"
    automatic_source = root / "automatic.mp3"
    first_download = downloads / "manual-candidate.mp3"
    second_download = downloads / "automatic-candidate.mp3"
    for path in (manual_source, automatic_source, first_download, second_download):
        path.write_bytes(b"audio")
    repositories.songs.save(SongMaster(id="song_manual", title="Manual Song", artist="Artist"))
    repositories.songs.save(SongMaster(id="song_auto", title="Auto Song", artist="Artist"))
    repositories.playlists.save(
        Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=(
                PlaylistItem(song_id="song_manual", position=1),
                PlaylistItem(song_id="song_auto", position=2),
            ),
        )
    )
    repositories.audio_files.save(_audio_file("manual_file", manual_source, title="Manual Song"))
    repositories.audio_files.save(_audio_file("auto_file", automatic_source, title="Auto Song"))
    repositories.match_links.save(
        MatchLink(
            song_id="song_manual",
            audio_file_id="manual_file",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )
    repositories.match_links.save(
        MatchLink(
            song_id="song_auto",
            audio_file_id="auto_file",
            method="metadata_exact",
            confidence=0.95,
        )
    )
    metadata_reader = FakeMetadataReader(
        {
            first_download: AudioMetadata(title="Manual Song", artist="Artist"),
            second_download: AudioMetadata(title="Auto Song", artist="Artist"),
        }
    )

    result = _match_downloads(repositories, metadata_reader).execute("env_1")

    assert result.matching.preserved_reviewed == 1
    assert result.matching.matched == 1
    manual_links = repositories.match_links.list_by_song("song_manual")
    auto_links = repositories.match_links.list_by_song("song_auto")
    assert manual_links == [
        MatchLink(
            song_id="song_manual",
            audio_file_id="manual_file",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    ]
    assert any(link.audio_file_id == "auto_file" for link in auto_links)
    assert any(link.audio_file_id != "auto_file" for link in auto_links)


class FakeMetadataReader:
    def __init__(self, metadata_by_path: dict[Path, AudioMetadata]) -> None:
        self.metadata_by_path = metadata_by_path

    def read(self, path: Path) -> AudioMetadata:
        return self.metadata_by_path.get(path, AudioMetadata())


class _Repositories:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.environments = SqliteEnvironmentRepository(connection)
        self.playlists = SqlitePlaylistRepository(connection)
        self.songs = SqliteSongRepository(connection)
        self.audio_files = SqliteAudioFileRepository(connection)
        self.match_links = SqliteMatchLinkRepository(connection)
        self.scan_runs = SqliteScanRunRepository(connection)


def _repositories(connection: sqlite3.Connection) -> _Repositories:
    return _Repositories(connection)


def _seed_environment(repositories: _Repositories, tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "usb"
    downloads = tmp_path / "downloads"
    root.mkdir()
    downloads.mkdir()
    repositories.environments.save(
        MusicEnvironment(
            id="env_1",
            name="USB",
            root_path=root,
            download_path=downloads,
        )
    )
    return root, downloads


def _seed_song_playlist(
    repositories: _Repositories,
    song: SongMaster,
    *items: PlaylistItem,
) -> None:
    repositories.songs.save(song)
    repositories.playlists.save(
        Playlist(
            id="playlist_1",
            environment_id="env_1",
            name="Set",
            items=items or (PlaylistItem(song_id=song.id, position=1),),
        )
    )


def _audio_file(audio_file_id: str, path: Path, *, title: str) -> AudioFile:
    return AudioFile(
        id=audio_file_id,
        environment_id="env_1",
        path=path,
        size_bytes=1,
        modified_at=1.0,
        title=title,
        artist="Artist",
    )


def _match_downloads(
    repositories: _Repositories,
    metadata_reader: FakeMetadataReader,
) -> MatchDownloads:
    return MatchDownloads(
        environments=repositories.environments,
        playlists=repositories.playlists,
        songs=repositories.songs,
        audio_files=repositories.audio_files,
        match_links=repositories.match_links,
        scan_runs=repositories.scan_runs,
        scanner_factory=LocalAudioScanner,
        metadata_reader=metadata_reader,
    )
