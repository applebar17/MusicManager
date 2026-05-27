from music_manager_backend.application.dtos import SoundCloudPlaylistImportResult
from music_manager_backend.application.use_cases.import_soundcloud_playlist import (
    SOUNDCLOUD_SOURCE,
    ImportSoundCloudPlaylist,
)
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    PlaylistRepository,
    RemotePlaylistRepository,
    SongRepository,
    SyncSnapshotRepository,
)
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class SyncSoundCloudPlaylist:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        remote_playlists: RemotePlaylistRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        sync_snapshots: SyncSnapshotRepository,
        importer: SoundCloudPlaylistImporter,
    ) -> None:
        self.environments = environments
        self.remote_playlists = remote_playlists
        self.playlists = playlists
        self.songs = songs
        self.sync_snapshots = sync_snapshots
        self.importer = importer

    def execute(self, environment_id: str, playlist_id: str) -> SoundCloudPlaylistImportResult:
        if self.environments.get(environment_id) is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        playlist = self.playlists.get(playlist_id)
        if playlist is None or playlist.environment_id != environment_id:
            raise NotFoundError(f"Playlist not found: {playlist_id}")
        if playlist.remote_playlist_id is None:
            raise ValidationError(
                f"Playlist is not backed by SoundCloud: {playlist_id}",
                code="playlist_not_soundcloud_backed",
            )

        remote_playlist = self.remote_playlists.get(playlist.remote_playlist_id)
        if remote_playlist is None:
            raise NotFoundError(f"Remote playlist not found: {playlist.remote_playlist_id}")
        if remote_playlist.source != SOUNDCLOUD_SOURCE:
            raise ValidationError(
                f"Playlist is not backed by SoundCloud: {playlist_id}",
                code="playlist_not_soundcloud_backed",
            )

        return ImportSoundCloudPlaylist(
            environments=self.environments,
            remote_playlists=self.remote_playlists,
            playlists=self.playlists,
            songs=self.songs,
            sync_snapshots=self.sync_snapshots,
            importer=self.importer,
        ).execute(environment_id, remote_playlist.source_url)
