from __future__ import annotations

from pathlib import Path
from typing import Protocol

from music_manager_backend.domain.entities import (
    AudioFile,
    ExportApplyRun,
    ExportPlan,
    LibraryAlignmentItem,
    LibraryAlignmentRun,
    LibraryTrack,
    LibraryTrackStatus,
    MatchLink,
    MusicEnvironment,
    MusicLibrary,
    Playlist,
    RemotePlaylist,
    ScanRun,
    SongMaster,
    SoundCloudSourceDiscovery,
    SyncSnapshot,
)
from music_manager_backend.domain.entities.audio_file import AudioFileStatus


class EnvironmentRepository(Protocol):
    def save(self, environment: MusicEnvironment) -> None:
        pass

    def get(self, environment_id: str) -> MusicEnvironment | None:
        pass

    def list(self, *, include_archived: bool = False) -> list[MusicEnvironment]:
        pass

    def archive(self, environment_id: str, archived_at: str) -> MusicEnvironment | None:
        pass


class RemotePlaylistRepository(Protocol):
    def save(self, remote_playlist: RemotePlaylist) -> None:
        pass

    def get(self, remote_playlist_id: str) -> RemotePlaylist | None:
        pass

    def get_by_source_url(self, source: str, source_url: str) -> RemotePlaylist | None:
        pass


class PlaylistRepository(Protocol):
    def save(self, playlist: Playlist) -> None:
        pass

    def get(self, playlist_id: str) -> Playlist | None:
        pass

    def list_by_environment(self, environment_id: str) -> list[Playlist]:
        pass

    def get_by_environment_remote_playlist(
        self, environment_id: str, remote_playlist_id: str
    ) -> Playlist | None:
        pass


class SongRepository(Protocol):
    def save(self, song: SongMaster) -> None:
        pass

    def get(self, song_id: str) -> SongMaster | None:
        pass

    def get_by_source_url(self, source_url: str) -> SongMaster | None:
        pass


class LibraryRepository(Protocol):
    def get_default(self) -> MusicLibrary | None:
        pass

    def save_default(self, library: MusicLibrary) -> None:
        pass


class LibraryTrackRepository(Protocol):
    def save(self, track: LibraryTrack) -> None:
        pass

    def get(self, track_id: str) -> LibraryTrack | None:
        pass

    def get_by_canonical_path(self, library_id: str, canonical_path: Path) -> LibraryTrack | None:
        pass

    def list(self, library_id: str) -> list[LibraryTrack]:
        pass

    def list_by_status(self, library_id: str, status: LibraryTrackStatus) -> list[LibraryTrack]:
        pass

    def count(self, library_id: str) -> int:
        pass

    def count_by_status(self, library_id: str, status: LibraryTrackStatus) -> int:
        pass

    def get_by_identity(
        self,
        library_id: str,
        normalized_title: str,
        duration_seconds: int,
    ) -> list[LibraryTrack]:
        pass


class LibraryAlignmentRunRepository(Protocol):
    def save(
        self,
        run: LibraryAlignmentRun,
        items: tuple[LibraryAlignmentItem, ...] = (),
    ) -> None:
        pass

    def get(self, run_id: str) -> tuple[LibraryAlignmentRun, tuple[LibraryAlignmentItem, ...]] | None:
        pass

    def latest(
        self,
        library_id: str,
    ) -> tuple[LibraryAlignmentRun, tuple[LibraryAlignmentItem, ...]] | None:
        pass


class SourceDiscoveryRepository(Protocol):
    def save(self, discovery: SoundCloudSourceDiscovery) -> None:
        pass

    def get(self, environment_id: str, song_id: str) -> SoundCloudSourceDiscovery | None:
        pass


class AudioFileRepository(Protocol):
    def save(self, audio_file: AudioFile) -> None:
        pass

    def get(self, audio_file_id: str) -> AudioFile | None:
        pass

    def get_by_environment_path(self, environment_id: str, path: Path) -> AudioFile | None:
        pass

    def list_by_environment(
        self,
        environment_id: str,
        *,
        status: AudioFileStatus | None = None,
    ) -> list[AudioFile]:
        pass

    def list_unmanaged_active_by_environment(self, environment_id: str) -> list[AudioFile]:
        pass


class ScanRunRepository(Protocol):
    def save(self, scan_run: ScanRun) -> None:
        pass

    def get(self, scan_run_id: str) -> ScanRun | None:
        pass


class MatchLinkRepository(Protocol):
    def save(self, match_link: MatchLink) -> None:
        pass

    def list_by_song(self, song_id: str) -> list[MatchLink]:
        pass

    def list_by_audio_file(self, audio_file_id: str) -> list[MatchLink]:
        pass

    def delete_automatic_by_song(self, song_id: str) -> None:
        pass

    def delete_automatic_by_song_audio_files(
        self, song_id: str, audio_file_ids: set[str]
    ) -> None:
        pass

    def delete_by_audio_file(self, audio_file_id: str) -> None:
        pass

    def replace_for_song(self, match_link: MatchLink) -> None:
        pass


class SyncSnapshotRepository(Protocol):
    def save(self, snapshot: SyncSnapshot) -> None:
        pass

    def list_by_remote_playlist(self, remote_playlist_id: str) -> list[SyncSnapshot]:
        pass


class ExportPlanRepository(Protocol):
    def save(self, export_plan: ExportPlan) -> None:
        pass

    def get(self, export_plan_id: str) -> ExportPlan | None:
        pass


class ExportApplyRunRepository(Protocol):
    def save(self, apply_run: ExportApplyRun) -> None:
        pass

    def get(self, apply_run_id: str) -> ExportApplyRun | None:
        pass
