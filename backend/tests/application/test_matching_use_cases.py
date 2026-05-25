import sqlite3
from pathlib import Path

import pytest

from music_manager_backend.application.use_cases.create_manual_mapping import CreateManualMapping
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.application.use_cases.run_matching import RunMatching
from music_manager_backend.domain.entities import (
    AudioFile,
    AudioFileStatus,
    MatchLink,
    MusicEnvironment,
    Playlist,
    PlaylistItem,
    SongMaster,
)
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteSongRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError


def test_run_matching_persists_unique_high_confidence_match(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(repositories, SongMaster(id="song_1", title="Track", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", title="Track", artist="Artist"))

    summary = _run_matching(repositories).execute("env_1")

    assert summary.matched == 1
    links = repositories.match_links.list_by_song("song_1")
    assert links == [
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="metadata_exact",
            confidence=0.95,
        )
    ]


def test_run_matching_marks_multiple_high_confidence_candidates_ambiguous(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(repositories, SongMaster(id="song_1", title="Track", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", title="Track", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_2", title="Track", artist="Artist"))

    summary = _run_matching(repositories).execute("env_1")

    assert summary.ambiguous == 1
    assert repositories.match_links.list_by_song("song_1") == []


def test_run_matching_marks_missing_audio(sqlite_connection: sqlite3.Connection) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(repositories, SongMaster(id="song_1", title="Missing", artist="Artist"))

    summary = _run_matching(repositories).execute("env_1")

    assert summary.missing_audio == 1


def test_playlist_folder_breaks_duplicate_title_duration_tie(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(
        repositories,
        SongMaster(
            id="song_1",
            title="Belpaese - Sentimento [Promo]",
            artist="Belpaese",
            duration_seconds=372,
        ),
        playlist_name="04_DANCE",
    )
    repositories.audio_files.save(
        _audio_file(
            "file_pop",
            path=Path("/Volumes/USB/08_POP/Belpaese - Sentimento [Promo].mp3"),
            title="Belpaese - Sentimento [Promo]",
            artist="Gare du Nord",
            duration_seconds=373,
        )
    )
    repositories.audio_files.save(
        _audio_file(
            "file_dance",
            path=Path("/Volumes/USB/04_DANCE/Belpaese - Sentimento [Promo].mp3"),
            title="Belpaese - Sentimento [Promo]",
            artist="Gare du Nord",
            duration_seconds=373,
        )
    )

    summary = _run_matching(repositories).execute("env_1")

    assert summary.matched == 1
    assert repositories.match_links.list_by_song("song_1") == [
        MatchLink(
            song_id="song_1",
            audio_file_id="file_dance",
            method="playlist_path_title_strict_duration",
            confidence=0.96,
        )
    ]


def test_playlist_folder_breaks_duplicate_metadata_exact_tie(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(
        repositories,
        SongMaster(
            id="song_1",
            title="Action (Single Edit) [feat. Cat Power & Mike D]",
            artist="Cassius",
            duration_seconds=233,
        ),
        playlist_name="03_HOUSE",
    )
    repositories.audio_files.save(
        _audio_file(
            "file_dance",
            path=Path(
                "/Volumes/USB/04_DANCE/Action (Single Edit) [feat. Cat Power & Mike D].mp3"
            ),
            title="Action (Single Edit) [feat. Cat Power & Mike D]",
            artist="CASSIUS",
            duration_seconds=233,
        )
    )
    repositories.audio_files.save(
        _audio_file(
            "file_house",
            path=Path(
                "/Volumes/USB/03_HOUSE/Action (Single Edit) [feat. Cat Power & Mike D].mp3"
            ),
            title="Action (Single Edit) [feat. Cat Power & Mike D]",
            artist="CASSIUS",
            duration_seconds=233,
        )
    )

    summary = _run_matching(repositories).execute("env_1")

    assert summary.matched == 1
    assert repositories.match_links.list_by_song("song_1") == [
        MatchLink(
            song_id="song_1",
            audio_file_id="file_house",
            method="playlist_path_metadata_exact",
            confidence=0.96,
        )
    ]


def test_run_matching_persists_unique_strict_title_duration_match(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(
        repositories,
        SongMaster(
            id="song_1",
            title="Strict Timing",
            artist="Remote Artist",
            duration_seconds=180,
        ),
    )
    repositories.audio_files.save(
        _audio_file(
            "file_1",
            title="Strict Timing",
            artist="Different Local Artist",
            duration_seconds=183,
        )
    )

    summary = _run_matching(repositories).execute("env_1")

    assert summary.matched == 1
    assert repositories.match_links.list_by_song("song_1") == [
        MatchLink(
            song_id="song_1",
            audio_file_id="file_1",
            method="title_strict_duration",
            confidence=0.95,
        )
    ]


def test_short_audio_candidate_warns_and_does_not_auto_match(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(repositories, SongMaster(id="song_1", title="Preview", artist="Artist"))
    repositories.audio_files.save(
        _audio_file(
            "file_preview",
            title="Preview",
            artist="Artist",
            duration_seconds=37,
        )
    )

    summary = _run_matching(repositories).execute("env_1")
    review = _list_review(repositories).execute("env_1")

    assert summary.ambiguous == 1
    assert repositories.match_links.list_by_song("song_1") == []
    assert review[0].status == "ambiguous"
    assert review[0].candidates[0].method == "likely_preview_metadata_exact"
    assert review[0].candidates[0].warnings == ["likely_preview_download"]


def test_manual_mapping_overrides_automatic_matching(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(repositories, SongMaster(id="song_1", title="Track", artist="Artist"))
    repositories.audio_files.save(_audio_file("manual_file", title="Other", artist="Other"))
    repositories.audio_files.save(_audio_file("auto_file", title="Track", artist="Artist"))
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="manual_file",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )

    summary = _run_matching(repositories).execute("env_1")
    review = _list_review(repositories).execute("env_1")

    assert summary.manually_mapped == 1
    assert review[0].status == "manually_mapped"
    assert review[0].match is not None
    assert review[0].match.audio_file_id == "manual_file"


def test_manual_mapping_is_ignored_when_audio_file_is_removed(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(repositories, SongMaster(id="song_1", title="Track", artist="Artist"))
    repositories.audio_files.save(
        _audio_file(
            "removed_file",
            title="Track",
            artist="Artist",
            status=AudioFileStatus.REMOVED,
        )
    )
    repositories.match_links.save(
        MatchLink(
            song_id="song_1",
            audio_file_id="removed_file",
            method="manual",
            confidence=1.0,
            reviewed=True,
        )
    )

    review = _list_review(repositories).execute("env_1")

    assert review[0].status == "missing_audio"
    assert review[0].match is None


def test_create_manual_mapping_validates_song_and_audio_file(
    sqlite_connection: sqlite3.Connection,
) -> None:
    repositories = _repositories(sqlite_connection)
    _seed_song_playlist(repositories, SongMaster(id="song_1", title="Track", artist="Artist"))
    repositories.audio_files.save(_audio_file("file_1", title="Track", artist="Artist"))
    use_case = _create_manual_mapping(repositories)

    row = use_case.execute("env_1", "song_1", "file_1")

    assert row.status == "manually_mapped"
    with pytest.raises(NotFoundError):
        use_case.execute("env_1", "song_missing", "file_1")
    with pytest.raises(ValidationError):
        use_case.execute("env_1", "song_1", "file_missing")


class _Repositories:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.environments = SqliteEnvironmentRepository(connection)
        self.playlists = SqlitePlaylistRepository(connection)
        self.songs = SqliteSongRepository(connection)
        self.audio_files = SqliteAudioFileRepository(connection)
        self.match_links = SqliteMatchLinkRepository(connection)


def _repositories(connection: sqlite3.Connection) -> _Repositories:
    return _Repositories(connection)


def _seed_song_playlist(
    repositories: _Repositories,
    song: SongMaster,
    *,
    playlist_name: str = "Set",
) -> None:
    repositories.environments.save(
        MusicEnvironment(id="env_1", name="USB", root_path=Path("/Volumes/USB"))
    )
    repositories.songs.save(song)
    repositories.playlists.save(
        Playlist(
            id="playlist_1",
            environment_id="env_1",
            name=playlist_name,
            items=(PlaylistItem(song_id=song.id, position=1),),
        )
    )


def _audio_file(
    audio_file_id: str,
    *,
    path: Path | None = None,
    title: str | None = None,
    artist: str | None = None,
    duration_seconds: int | None = None,
    status: AudioFileStatus = AudioFileStatus.ACTIVE,
) -> AudioFile:
    return AudioFile(
        id=audio_file_id,
        environment_id="env_1",
        path=path or Path(f"/Volumes/USB/{audio_file_id}.mp3"),
        size_bytes=1,
        modified_at=1.0,
        title=title,
        artist=artist,
        duration_seconds=duration_seconds,
        status=status,
    )


def _run_matching(repositories: _Repositories) -> RunMatching:
    return RunMatching(
        environments=repositories.environments,
        playlists=repositories.playlists,
        songs=repositories.songs,
        audio_files=repositories.audio_files,
        match_links=repositories.match_links,
    )


def _list_review(repositories: _Repositories) -> ListMatchReview:
    return ListMatchReview(
        environments=repositories.environments,
        playlists=repositories.playlists,
        songs=repositories.songs,
        audio_files=repositories.audio_files,
        match_links=repositories.match_links,
    )


def _create_manual_mapping(repositories: _Repositories) -> CreateManualMapping:
    return CreateManualMapping(
        environments=repositories.environments,
        playlists=repositories.playlists,
        songs=repositories.songs,
        audio_files=repositories.audio_files,
        match_links=repositories.match_links,
    )
