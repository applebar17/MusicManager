from music_manager_backend.application.dtos import (
    SoundCloudDiscoveryLinkRead,
    SoundCloudTrackDiscoveryRead,
)
from music_manager_backend.application.use_cases.matching_common import load_environment_songs
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    PlaylistRepository,
    SongRepository,
)
from music_manager_backend.ports.soundcloud_discovery import SoundCloudTrackDiscoveryProvider
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class DiscoverSoundCloudTrack:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        discovery_provider: SoundCloudTrackDiscoveryProvider,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.discovery_provider = discovery_provider

    def execute(self, environment_id: str, song_id: str) -> SoundCloudTrackDiscoveryRead:
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        songs_by_id = {song.id: song for song in environment_songs.songs}
        song = songs_by_id.get(song_id)
        if song is None:
            raise NotFoundError(f"Song not found in environment: {song_id}")
        if not song.source_url:
            raise ValidationError(
                f"Song is not backed by a SoundCloud URL: {song_id}",
                code="song_missing_soundcloud_source_url",
            )

        discovery = self.discovery_provider.discover_track(song.source_url)
        title = discovery.title or song.display_title
        artist = discovery.artist or song.display_artist
        return SoundCloudTrackDiscoveryRead(
            environment_id=environment_id,
            song_id=song.id,
            track_url=discovery.track_url,
            track_urn=discovery.track_urn,
            title=title,
            artist=artist,
            description=discovery.description,
            purchase_title=discovery.purchase_title,
            purchase_url=discovery.purchase_url,
            downloadable=discovery.downloadable,
            download_url=discovery.download_url,
            links=[
                SoundCloudDiscoveryLinkRead(
                    url=link.url,
                    label=link.label,
                    kind=link.kind,
                    source=link.source,
                )
                for link in discovery.links
            ],
            tags=list(discovery.tags),
            release_metadata=discovery.release_metadata,
            warnings=list(discovery.warnings),
        )
