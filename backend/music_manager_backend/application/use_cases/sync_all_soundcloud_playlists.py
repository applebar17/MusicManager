from music_manager_backend.application.dtos import (
    SoundCloudPlaylistSyncAllResult,
    SoundCloudPlaylistSyncItemResult,
)
from music_manager_backend.application.use_cases.import_soundcloud_playlist import (
    SOUNDCLOUD_SOURCE,
    ImportSoundCloudPlaylist,
)
from music_manager_backend.domain.entities import Playlist, RemotePlaylist
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    PlaylistRepository,
    RemotePlaylistRepository,
    SongRepository,
    SyncSnapshotRepository,
)
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter
from music_manager_backend.shared.errors import MusicManagerError, NotFoundError


class SyncAllSoundCloudPlaylists:
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

    def execute(self, environment_id: str) -> SoundCloudPlaylistSyncAllResult:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        candidates = self._soundcloud_playlists(environment_id)
        results = tuple(
            self._sync_playlist(environment_id, playlist=playlist, remote_playlist=remote)
            for playlist, remote in candidates
        )
        succeeded = sum(1 for result in results if result.status == "synced")
        failed = sum(1 for result in results if result.status == "failed")

        return SoundCloudPlaylistSyncAllResult(
            environment_id=environment_id,
            total=len(results),
            succeeded=succeeded,
            failed=failed,
            results=results,
        )

    def _soundcloud_playlists(
        self, environment_id: str
    ) -> list[tuple[Playlist, RemotePlaylist]]:
        candidates: list[tuple[Playlist, RemotePlaylist]] = []
        for playlist in self.playlists.list_by_environment(environment_id):
            if playlist.remote_playlist_id is None:
                continue
            remote = self.remote_playlists.get(playlist.remote_playlist_id)
            if remote is None or remote.source != SOUNDCLOUD_SOURCE:
                continue
            candidates.append((playlist, remote))
        return candidates

    def _sync_playlist(
        self,
        environment_id: str,
        *,
        playlist: Playlist,
        remote_playlist: RemotePlaylist,
    ) -> SoundCloudPlaylistSyncItemResult:
        try:
            result = ImportSoundCloudPlaylist(
                environments=self.environments,
                remote_playlists=self.remote_playlists,
                playlists=self.playlists,
                songs=self.songs,
                sync_snapshots=self.sync_snapshots,
                importer=self.importer,
            ).execute(environment_id, remote_playlist.source_url)
        except MusicManagerError as exc:
            return SoundCloudPlaylistSyncItemResult(
                playlist_id=playlist.id,
                remote_playlist_id=remote_playlist.id,
                source_url=remote_playlist.source_url,
                status="failed",
                playlist_name=playlist.display_name,
                error_code=exc.code,
                error_message=exc.message,
            )

        return SoundCloudPlaylistSyncItemResult(
            playlist_id=result.playlist_id,
            remote_playlist_id=result.remote_playlist_id,
            source_url=remote_playlist.source_url,
            status="synced",
            playlist_name=result.playlist_name,
            track_count=result.track_count,
            added=result.added,
            removed=result.removed,
            reactivated=result.reactivated,
            reordered=result.reordered,
            metadata_changed=result.metadata_changed,
            unchanged=result.unchanged,
            warnings=result.warnings,
        )
