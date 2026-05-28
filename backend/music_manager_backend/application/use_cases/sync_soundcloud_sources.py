from music_manager_backend.application.dtos import (
    SoundCloudSourceSyncItemRead,
    SoundCloudSourceSyncResultRead,
)
from music_manager_backend.application.use_cases.discover_soundcloud_track import (
    DiscoverSoundCloudTrack,
)
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.application.use_cases.matching_common import load_environment_songs
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
    SourceDiscoveryRepository,
)
from music_manager_backend.ports.soundcloud_discovery import SoundCloudTrackDiscoveryProvider
from music_manager_backend.shared.errors import MusicManagerError


class SyncMissingSoundCloudSources:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
        source_discoveries: SourceDiscoveryRepository,
        discovery_provider: SoundCloudTrackDiscoveryProvider,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links
        self.source_discoveries = source_discoveries
        self.discovery_provider = discovery_provider

    def execute(self, environment_id: str) -> SoundCloudSourceSyncResultRead:
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        rows = ListMatchReview(
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
            audio_files=self.audio_files,
            match_links=self.match_links,
            source_discoveries=self.source_discoveries,
        ).execute(environment_id)
        songs_by_id = {song.id: song for song in environment_songs.songs}
        results: list[SoundCloudSourceSyncItemRead] = []

        discover = DiscoverSoundCloudTrack(
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
            source_discoveries=self.source_discoveries,
            discovery_provider=self.discovery_provider,
        )

        for row in rows:
            if row.status not in {"missing_audio", "ambiguous"}:
                continue
            song = songs_by_id.get(row.song_id)
            if song is None:
                continue
            if not song.source_url:
                results.append(
                    SoundCloudSourceSyncItemRead(
                        song_id=song.id,
                        title=song.display_title,
                        status="skipped",
                        error_code="song_missing_soundcloud_source_url",
                        error_message="Song is not backed by a SoundCloud URL.",
                    )
                )
                continue

            stored = self.source_discoveries.get(environment_id, song.id)
            if stored is not None and stored.has_source_link:
                results.append(
                    SoundCloudSourceSyncItemRead(
                        song_id=song.id,
                        title=song.display_title,
                        status="skipped",
                        source_url=song.source_url,
                        discovered_url=stored.best_source_url,
                    )
                )
                continue

            try:
                discovery = discover.execute(environment_id, song.id)
            except MusicManagerError as exc:
                results.append(
                    SoundCloudSourceSyncItemRead(
                        song_id=song.id,
                        title=song.display_title,
                        status="failed",
                        source_url=song.source_url,
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                )
                continue
            except Exception as exc:
                results.append(
                    SoundCloudSourceSyncItemRead(
                        song_id=song.id,
                        title=song.display_title,
                        status="failed",
                        source_url=song.source_url,
                        error_code="unexpected_error",
                        error_message=str(exc) or "Unexpected source discovery failure.",
                    )
                )
                continue
            results.append(
                SoundCloudSourceSyncItemRead(
                    song_id=song.id,
                    title=song.display_title,
                    status="discovered",
                    source_url=song.source_url,
                    discovered_url=_best_source_url(discovery),
                )
            )

        return SoundCloudSourceSyncResultRead(
            environment_id=environment_id,
            total=len(results),
            discovered=sum(1 for result in results if result.status == "discovered"),
            skipped=sum(1 for result in results if result.status == "skipped"),
            failed=sum(1 for result in results if result.status == "failed"),
            results=results,
        )


def _best_source_url(discovery: object) -> str | None:
    purchase_url = getattr(discovery, "purchase_url", None)
    if isinstance(purchase_url, str) and purchase_url:
        return purchase_url
    download_url = getattr(discovery, "download_url", None)
    if isinstance(download_url, str) and download_url:
        return download_url
    links = getattr(discovery, "links", None)
    if not isinstance(links, list):
        return None
    for link in links:
        kind = getattr(link, "kind", None)
        url = getattr(link, "url", None)
        if kind in {"download", "buy", "buy_or_download"} and isinstance(url, str):
            return url
    return None
