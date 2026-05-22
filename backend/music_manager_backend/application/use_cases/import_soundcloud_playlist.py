from dataclasses import dataclass

from music_manager_backend.application.dtos import SoundCloudPlaylistImportResult
from music_manager_backend.domain.entities import (
    Playlist,
    PlaylistItem,
    RemotePlaylist,
    SongMaster,
    SyncSnapshot,
)
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    PlaylistRepository,
    RemotePlaylistRepository,
    SongRepository,
    SyncSnapshotRepository,
)
from music_manager_backend.ports.soundcloud import SoundCloudPlaylistImporter
from music_manager_backend.ports.soundcloud_models import (
    ParsedSoundCloudPlaylist,
    ParsedSoundCloudTrack,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError
from music_manager_backend.shared.ids import new_id

SOUNDCLOUD_SOURCE = "soundcloud"


@dataclass(frozen=True)
class _TrackImport:
    track: ParsedSoundCloudTrack
    song: SongMaster
    metadata_changed: bool


class ImportSoundCloudPlaylist:
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

    def execute(self, environment_id: str, url: str) -> SoundCloudPlaylistImportResult:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        parsed = self.importer.import_playlist(url)
        if not parsed.tracks:
            raise ValidationError("SoundCloud playlist import did not discover any tracks")

        playlist_name = parsed.title or parsed.source_url
        remote_playlist = self._save_remote_playlist(parsed, playlist_name)
        existing_playlist = self.playlists.get_by_environment_remote_playlist(
            environment_id, remote_playlist.id
        )
        imported_tracks = tuple(self._save_song(track) for track in parsed.tracks)
        playlist = self._save_playlist(
            environment_id=environment_id,
            remote_playlist=remote_playlist,
            playlist_name=playlist_name,
            existing_playlist=existing_playlist,
            imported_tracks=imported_tracks,
        )
        snapshot = self._save_snapshot(remote_playlist, parsed)

        counts = _diff_counts(existing_playlist, imported_tracks)
        metadata_changed = sum(1 for item in imported_tracks if item.metadata_changed)
        unchanged = _unchanged_count(existing_playlist, imported_tracks)

        return SoundCloudPlaylistImportResult(
            environment_id=environment_id,
            remote_playlist_id=remote_playlist.id,
            playlist_id=playlist.id,
            sync_snapshot_id=snapshot.id,
            playlist_name=playlist.display_name,
            track_count=len(parsed.tracks),
            added=counts.added,
            removed=counts.removed,
            reactivated=counts.reactivated,
            reordered=counts.reordered,
            metadata_changed=metadata_changed,
            unchanged=unchanged,
            warnings=parsed.warnings,
        )

    def _save_remote_playlist(
        self, parsed: ParsedSoundCloudPlaylist, playlist_name: str
    ) -> RemotePlaylist:
        existing = self.remote_playlists.get_by_source_url(SOUNDCLOUD_SOURCE, parsed.source_url)
        remote_playlist = RemotePlaylist(
            id=existing.id if existing else new_id("remote_playlist"),
            source=SOUNDCLOUD_SOURCE,
            source_url=parsed.source_url,
            name=playlist_name,
        )
        self.remote_playlists.save(remote_playlist)
        return remote_playlist

    def _save_song(self, track: ParsedSoundCloudTrack) -> _TrackImport:
        existing = self.songs.get_by_source_url(track.canonical_track_url)
        metadata_changed = False
        if existing is None:
            song = SongMaster(
                id=new_id("song"),
                title=track.title,
                artist=track.uploader,
                duration_seconds=track.duration_seconds,
                source_track_id=track.canonical_track_url,
                source_url=track.canonical_track_url,
            )
        else:
            metadata_changed = (
                existing.title != track.title
                or existing.artist != track.uploader
                or existing.duration_seconds != track.duration_seconds
            )
            song = SongMaster(
                id=existing.id,
                title=track.title,
                artist=track.uploader,
                duration_seconds=track.duration_seconds,
                source_track_id=existing.source_track_id or track.canonical_track_url,
                source_url=track.canonical_track_url,
                local_title_override=existing.local_title_override,
                local_artist_override=existing.local_artist_override,
            )

        self.songs.save(song)
        return _TrackImport(track=track, song=song, metadata_changed=metadata_changed)

    def _save_playlist(
        self,
        *,
        environment_id: str,
        remote_playlist: RemotePlaylist,
        playlist_name: str,
        existing_playlist: Playlist | None,
        imported_tracks: tuple[_TrackImport, ...],
    ) -> Playlist:
        existing_items = {
            item.song_id: item
            for item in (existing_playlist.items if existing_playlist is not None else ())
        }
        imported_song_ids = {item.song.id for item in imported_tracks}
        items = [
            PlaylistItem(
                song_id=item.song.id,
                position=item.track.position,
                remote_membership_active=True,
            )
            for item in imported_tracks
        ]
        items.extend(
            PlaylistItem(
                song_id=item.song_id,
                position=item.position,
                remote_membership_active=False,
            )
            for item in existing_items.values()
            if item.song_id not in imported_song_ids
        )
        playlist = Playlist(
            id=existing_playlist.id if existing_playlist else new_id("playlist"),
            environment_id=environment_id,
            name=playlist_name,
            remote_playlist_id=remote_playlist.id,
            local_name_override=(
                existing_playlist.local_name_override if existing_playlist is not None else None
            ),
            items=tuple(items),
        )
        self.playlists.save(playlist)
        return playlist

    def _save_snapshot(
        self, remote_playlist: RemotePlaylist, parsed: ParsedSoundCloudPlaylist
    ) -> SyncSnapshot:
        snapshot = SyncSnapshot(
            id=new_id("sync_snapshot"),
            source=SOUNDCLOUD_SOURCE,
            remote_playlist_id=remote_playlist.id,
            payload=_snapshot_payload(parsed),
        )
        self.sync_snapshots.save(snapshot)
        return snapshot


@dataclass(frozen=True)
class _DiffCounts:
    added: int
    removed: int
    reactivated: int
    reordered: int


def _diff_counts(
    existing_playlist: Playlist | None, imported_tracks: tuple[_TrackImport, ...]
) -> _DiffCounts:
    if existing_playlist is None:
        return _DiffCounts(
            added=len(imported_tracks),
            removed=0,
            reactivated=0,
            reordered=0,
        )

    existing_items = {item.song_id: item for item in existing_playlist.items}
    imported_song_ids = {item.song.id for item in imported_tracks}
    added = 0
    reactivated = 0
    reordered = 0
    for item in imported_tracks:
        existing_item = existing_items.get(item.song.id)
        if existing_item is None:
            added += 1
        elif not existing_item.remote_membership_active:
            reactivated += 1
        elif existing_item.position != item.track.position:
            reordered += 1

    removed = sum(
        1
        for item in existing_items.values()
        if item.remote_membership_active and item.song_id not in imported_song_ids
    )
    return _DiffCounts(
        added=added,
        removed=removed,
        reactivated=reactivated,
        reordered=reordered,
    )


def _unchanged_count(
    existing_playlist: Playlist | None, imported_tracks: tuple[_TrackImport, ...]
) -> int:
    if existing_playlist is None:
        return 0

    existing_items = {item.song_id: item for item in existing_playlist.items}
    unchanged = 0
    for item in imported_tracks:
        existing_item = existing_items.get(item.song.id)
        if (
            existing_item is not None
            and existing_item.remote_membership_active
            and existing_item.position == item.track.position
            and not item.metadata_changed
        ):
            unchanged += 1
    return unchanged


def _snapshot_payload(parsed: ParsedSoundCloudPlaylist) -> dict[str, object]:
    return {
        "source_url": parsed.source_url,
        "title": parsed.title,
        "warnings": list(parsed.warnings),
        "tracks": [
            {
                "position": track.position,
                "title": track.title,
                "uploader": track.uploader,
                "uploader_url": track.uploader_url,
                "canonical_track_url": track.canonical_track_url,
                "playlist_track_url": track.playlist_track_url,
                "artwork_url": track.artwork_url,
                "play_count": track.play_count,
                "duration_seconds": track.duration_seconds,
                "raw": track.raw,
            }
            for track in parsed.tracks
        ],
    }
