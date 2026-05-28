from music_manager_backend.application.dtos import (
    SoundCloudDiscoveryLinkRead,
    SoundCloudTrackDiscoveryRead,
)
from music_manager_backend.application.use_cases.matching_common import load_environment_songs
from music_manager_backend.domain.entities import SongMaster, SoundCloudSourceDiscovery
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    PlaylistRepository,
    SongRepository,
    SourceDiscoveryRepository,
)
from music_manager_backend.ports.soundcloud_discovery import (
    SoundCloudTrackDiscovery,
    SoundCloudTrackDiscoveryProvider,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError
from music_manager_backend.shared.time import utc_now_iso


class DiscoverSoundCloudTrack:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        source_discoveries: SourceDiscoveryRepository,
        discovery_provider: SoundCloudTrackDiscoveryProvider,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.source_discoveries = source_discoveries
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
        stored = _stored_discovery_from_provider(
            environment_id=environment_id,
            song=song,
            discovery=discovery,
        )
        self.source_discoveries.save(stored)
        return soundcloud_discovery_read(stored, fallback_song=song)


def soundcloud_discovery_read(
    discovery: SoundCloudSourceDiscovery,
    *,
    fallback_song: SongMaster,
) -> SoundCloudTrackDiscoveryRead:
    title = discovery.title or fallback_song.display_title
    artist = discovery.artist or fallback_song.display_artist
    return SoundCloudTrackDiscoveryRead(
        environment_id=discovery.environment_id,
        song_id=discovery.song_id,
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
        fetched_at=discovery.fetched_at,
    )


def _stored_discovery_from_provider(
    *,
    environment_id: str,
    song: SongMaster,
    discovery: SoundCloudTrackDiscovery,
) -> SoundCloudSourceDiscovery:
    return SoundCloudSourceDiscovery(
        environment_id=environment_id,
        song_id=song.id,
        track_url=discovery.track_url,
        track_urn=discovery.track_urn,
        title=discovery.title,
        artist=discovery.artist,
        description=discovery.description,
        purchase_title=discovery.purchase_title,
        purchase_url=discovery.purchase_url,
        downloadable=discovery.downloadable,
        download_url=discovery.download_url,
        links=discovery.links,
        tags=discovery.tags,
        release_metadata=discovery.release_metadata,
        warnings=discovery.warnings,
        raw=discovery.raw,
        fetched_at=utc_now_iso(),
    )


def stored_discovery_read(
    *,
    environment_id: str,
    song: SongMaster,
    source_discoveries: SourceDiscoveryRepository,
) -> SoundCloudTrackDiscoveryRead | None:
    discovery = source_discoveries.get(environment_id, song.id)
    if discovery is None:
        return None
    return soundcloud_discovery_read(discovery, fallback_song=song)
