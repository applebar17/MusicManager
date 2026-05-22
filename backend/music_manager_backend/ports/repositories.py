from typing import Protocol

from music_manager_backend.domain.entities import (
    AudioFile,
    ExportPlan,
    MatchLink,
    MusicEnvironment,
    Playlist,
    RemotePlaylist,
    SongMaster,
    SyncSnapshot,
)


class EnvironmentRepository(Protocol):
    def save(self, environment: MusicEnvironment) -> None:
        pass

    def get(self, environment_id: str) -> MusicEnvironment | None:
        pass

    def list(self) -> list[MusicEnvironment]:
        pass


class RemotePlaylistRepository(Protocol):
    def save(self, remote_playlist: RemotePlaylist) -> None:
        pass

    def get(self, remote_playlist_id: str) -> RemotePlaylist | None:
        pass


class PlaylistRepository(Protocol):
    def save(self, playlist: Playlist) -> None:
        pass

    def get(self, playlist_id: str) -> Playlist | None:
        pass

    def list_by_environment(self, environment_id: str) -> list[Playlist]:
        pass


class SongRepository(Protocol):
    def save(self, song: SongMaster) -> None:
        pass

    def get(self, song_id: str) -> SongMaster | None:
        pass


class AudioFileRepository(Protocol):
    def save(self, audio_file: AudioFile) -> None:
        pass

    def get(self, audio_file_id: str) -> AudioFile | None:
        pass

    def list_by_environment(self, environment_id: str) -> list[AudioFile]:
        pass


class MatchLinkRepository(Protocol):
    def save(self, match_link: MatchLink) -> None:
        pass

    def list_by_song(self, song_id: str) -> list[MatchLink]:
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
