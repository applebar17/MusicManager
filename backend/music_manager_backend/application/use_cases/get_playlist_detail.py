from pathlib import Path

from music_manager_backend.application.dtos import (
    MatchReviewRow,
    PlaylistDetailRead,
    PlaylistItemRead,
)
from music_manager_backend.application.use_cases.discover_soundcloud_track import (
    stored_discovery_read,
)
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.application.use_cases.match_link_selection import preferred_match_link
from music_manager_backend.application.use_cases.matching_common import active_audio_files_by_id
from music_manager_backend.domain.entities import (
    AudioFile,
    MatchStatus,
    MusicEnvironment,
    PlaylistItem,
    SongMaster,
)
from music_manager_backend.domain.services.audio_quality import audio_warnings
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    LibraryRepository,
    LibraryTrackRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongLibraryLinkRepository,
    SongRepository,
    SourceDiscoveryRepository,
)
from music_manager_backend.shared.errors import NotFoundError


class GetPlaylistDetail:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
        source_discoveries: SourceDiscoveryRepository | None = None,
        libraries: LibraryRepository | None = None,
        library_tracks: LibraryTrackRepository | None = None,
        song_library_links: SongLibraryLinkRepository | None = None,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links
        self.source_discoveries = source_discoveries
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.song_library_links = song_library_links

    def execute(self, environment_id: str, playlist_id: str) -> PlaylistDetailRead:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        playlist = self.playlists.get(playlist_id)
        if playlist is None or playlist.environment_id != environment_id:
            raise NotFoundError(f"Playlist not found: {playlist_id}")

        review_by_song = {
            row.song_id: row
            for row in ListMatchReview(
                environments=self.environments,
                playlists=self.playlists,
                songs=self.songs,
                audio_files=self.audio_files,
                match_links=self.match_links,
                source_discoveries=self.source_discoveries,
                libraries=self.libraries,
                library_tracks=self.library_tracks,
                song_library_links=self.song_library_links,
            ).execute(environment_id)
        }
        items: list[PlaylistItemRead] = []
        removed_items: list[PlaylistItemRead] = []
        active_files = active_audio_files_by_id(
            environment_id=environment_id,
            audio_files=self.audio_files,
        )
        for item in sorted(playlist.items, key=lambda value: (value.position, value.song_id)):
            song = self.songs.get(item.song_id)
            if song is None:
                continue
            review = review_by_song.get(item.song_id)
            read = _playlist_item_read(
                environment=environment,
                environment_id=environment_id,
                item=item,
                song=song,
                review=review,
                active_files=active_files,
                match_links=self.match_links,
                source_discoveries=self.source_discoveries,
            )
            if item.is_active:
                items.append(read)
            elif item.is_removed_history:
                removed_items.append(read)
        return PlaylistDetailRead(
            id=playlist.id,
            environment_id=environment_id,
            name=playlist.display_name,
            remote_playlist_id=playlist.remote_playlist_id,
            active_item_count=sum(1 for item in playlist.items if item.is_active),
            inactive_item_count=sum(1 for item in playlist.items if item.is_removed_history),
            items=items,
            removed_items=removed_items,
        )


def _accepted_audio_filename(path: str) -> str:
    return Path(path).name


def _accepted_audio_relative_path(path: str, root_path: Path) -> str:
    audio_path = Path(path)
    try:
        return audio_path.relative_to(root_path).as_posix()
    except ValueError:
        return audio_path.name


def _playlist_item_read(
    *,
    environment: MusicEnvironment,
    environment_id: str,
    item: PlaylistItem,
    song: SongMaster,
    review: MatchReviewRow | None,
    active_files: dict[str, AudioFile],
    match_links: MatchLinkRepository,
    source_discoveries: SourceDiscoveryRepository | None,
) -> PlaylistItemRead:
    match_status = "missing_audio"
    accepted_audio_file_id = None
    accepted_audio_filename = None
    accepted_audio_relative_path = None
    accepted_audio_warnings: list[str] = []
    library_match_status = None
    accepted_library_track_id = None
    accepted_library_filename = None
    accepted_library_path = None

    if review is not None:
        match_status = review.status
        library_match_status = review.library_status
        if review.library_match is not None:
            accepted_library_track_id = review.library_match.library_track_id
            accepted_library_filename = review.library_match.filename
            accepted_library_path = review.library_match.path
        if review.match is not None:
            accepted_audio_file_id = review.match.audio_file_id
            accepted_audio_filename = _accepted_audio_filename(review.match.path)
            accepted_audio_relative_path = _accepted_audio_relative_path(
                review.match.path,
                environment.root_path,
            )
            accepted_audio_warnings = review.match.warnings
    else:
        accepted = preferred_match_link(match_links.list_by_song(song.id), active_files)
        if accepted is not None:
            audio_file = active_files[accepted.audio_file_id]
            match_status = (
                MatchStatus.MANUALLY_MAPPED.value
                if accepted.reviewed and accepted.method == "manual"
                else MatchStatus.MATCHED.value
            )
            accepted_audio_file_id = audio_file.id
            accepted_audio_filename = _accepted_audio_filename(str(audio_file.path))
            accepted_audio_relative_path = _accepted_audio_relative_path(
                str(audio_file.path),
                environment.root_path,
            )
            accepted_audio_warnings = audio_warnings(audio_file.duration_seconds)

    return PlaylistItemRead(
        song_id=song.id,
        position=item.position,
        title=song.display_title,
        artist=song.display_artist,
        duration_seconds=song.duration_seconds,
        remote_membership_active=item.remote_membership_active,
        local_membership_active=item.local_membership_active,
        added_by_local_audio_file_id=item.added_by_local_audio_file_id,
        remote_removed_at=item.remote_removed_at,
        match_status=match_status,
        accepted_audio_file_id=accepted_audio_file_id,
        accepted_audio_filename=accepted_audio_filename,
        accepted_audio_relative_path=accepted_audio_relative_path,
        accepted_audio_warnings=accepted_audio_warnings,
        library_match_status=library_match_status,
        accepted_library_track_id=accepted_library_track_id,
        accepted_library_filename=accepted_library_filename,
        accepted_library_path=accepted_library_path,
        playback_url=(
            f"/environments/{environment_id}/playback/audio-files/{accepted_audio_file_id}"
            if accepted_audio_file_id is not None
            else None
        ),
        source_discovery=(
            stored_discovery_read(
                environment_id=environment_id,
                song=song,
                source_discoveries=source_discoveries,
            )
            if source_discoveries is not None
            else None
        ),
    )
