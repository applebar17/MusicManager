from pathlib import Path

from music_manager_backend.application.dtos import PlaylistDetailRead
from music_manager_backend.application.use_cases.get_playlist_detail import GetPlaylistDetail
from music_manager_backend.domain.entities import (
    AudioFile,
    AudioFileStatus,
    MatchLink,
    Playlist,
    PlaylistItem,
    SongMaster,
)
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
    SourceDiscoveryRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError
from music_manager_backend.shared.ids import new_id


class AddPlaylistLocalItem:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
        source_discoveries: SourceDiscoveryRepository | None = None,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links
        self.source_discoveries = source_discoveries

    def execute(
        self,
        environment_id: str,
        playlist_id: str,
        audio_file_id: str,
    ) -> PlaylistDetailRead:
        _environment_or_raise(self.environments, environment_id)
        playlist = _playlist_or_raise(self.playlists, environment_id, playlist_id)
        audio_file = _active_audio_file_or_raise(
            self.audio_files,
            environment_id,
            audio_file_id,
        )
        song = self._song_for_audio_file(audio_file)
        existing = next((item for item in playlist.items if item.song_id == song.id), None)
        if existing is not None and existing.is_active:
            raise ValidationError(
                "This song is already active in the playlist.",
                code="playlist_item_already_active",
            )

        self.match_links.replace_for_song(
            MatchLink(
                song_id=song.id,
                audio_file_id=audio_file.id,
                method="manual",
                confidence=1.0,
                reviewed=True,
            )
        )
        position = _next_active_position(playlist)
        updated_item = PlaylistItem(
            song_id=song.id,
            position=position,
            remote_membership_active=existing.remote_membership_active if existing else False,
            local_membership_active=True,
            added_by_local_audio_file_id=audio_file.id,
            remote_removed_at=existing.remote_removed_at if existing else None,
        )
        updated_items = tuple(
            updated_item if item.song_id == song.id else item for item in playlist.items
        )
        if existing is None:
            updated_items = (*playlist.items, updated_item)
        self.playlists.save(_playlist_with_items(playlist, updated_items))
        return _detail(
            environment_id=environment_id,
            playlist_id=playlist_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
            audio_files=self.audio_files,
            match_links=self.match_links,
            source_discoveries=self.source_discoveries,
        )

    def _song_for_audio_file(self, audio_file: AudioFile) -> SongMaster:
        for link in self.match_links.list_by_audio_file(audio_file.id):
            song = self.songs.get(link.song_id)
            if song is not None:
                return song

        song = SongMaster(
            id=new_id("song"),
            title=audio_file.title or Path(audio_file.path).stem,
            artist=audio_file.artist,
            duration_seconds=audio_file.duration_seconds,
        )
        self.songs.save(song)
        return song


class RemovePlaylistLocalItem:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
        source_discoveries: SourceDiscoveryRepository | None = None,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links
        self.source_discoveries = source_discoveries

    def execute(self, environment_id: str, playlist_id: str, song_id: str) -> PlaylistDetailRead:
        _environment_or_raise(self.environments, environment_id)
        playlist = _playlist_or_raise(self.playlists, environment_id, playlist_id)
        existing = next((item for item in playlist.items if item.song_id == song_id), None)
        if existing is None or not existing.local_membership_active:
            raise ValidationError(
                "This song does not have local membership in the playlist.",
                code="playlist_local_item_not_active",
            )

        if not existing.remote_membership_active and existing.remote_removed_at is None:
            updated_items = tuple(item for item in playlist.items if item.song_id != existing.song_id)
        else:
            updated_item = PlaylistItem(
                song_id=existing.song_id,
                position=existing.position,
                remote_membership_active=existing.remote_membership_active,
                local_membership_active=False,
                added_by_local_audio_file_id=None,
                remote_removed_at=existing.remote_removed_at,
            )
            updated_items = tuple(
                updated_item if item.song_id == existing.song_id else item
                for item in playlist.items
            )
        self.playlists.save(_playlist_with_items(playlist, updated_items))
        return _detail(
            environment_id=environment_id,
            playlist_id=playlist_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
            audio_files=self.audio_files,
            match_links=self.match_links,
            source_discoveries=self.source_discoveries,
        )


def _playlist_or_raise(
    playlists: PlaylistRepository,
    environment_id: str,
    playlist_id: str,
) -> Playlist:
    playlist = playlists.get(playlist_id)
    if playlist is None or playlist.environment_id != environment_id:
        raise NotFoundError(f"Playlist not found: {playlist_id}")
    return playlist


def _environment_or_raise(
    environments: EnvironmentRepository,
    environment_id: str,
) -> None:
    if environments.get(environment_id) is None:
        raise NotFoundError(f"Environment not found: {environment_id}")


def _active_audio_file_or_raise(
    audio_files: AudioFileRepository,
    environment_id: str,
    audio_file_id: str,
) -> AudioFile:
    audio_file = audio_files.get(audio_file_id)
    if audio_file is None or audio_file.environment_id != environment_id:
        raise NotFoundError(f"Audio file not found: {audio_file_id}")
    if audio_file.status != AudioFileStatus.ACTIVE:
        raise ValidationError(
            f"Audio file is not active: {audio_file_id}",
            code="audio_file_not_active",
        )
    return audio_file


def _next_active_position(playlist: Playlist) -> int:
    active_positions = [item.position for item in playlist.items if item.is_active]
    return max(active_positions, default=0) + 1


def _playlist_with_items(playlist: Playlist, items: tuple[PlaylistItem, ...]) -> Playlist:
    return Playlist(
        id=playlist.id,
        environment_id=playlist.environment_id,
        name=playlist.name,
        remote_playlist_id=playlist.remote_playlist_id,
        local_name_override=playlist.local_name_override,
        items=items,
    )


def _detail(
    *,
    environment_id: str,
    playlist_id: str,
    environments: EnvironmentRepository,
    playlists: PlaylistRepository,
    songs: SongRepository,
    audio_files: AudioFileRepository,
    match_links: MatchLinkRepository,
    source_discoveries: SourceDiscoveryRepository | None,
) -> PlaylistDetailRead:
    return GetPlaylistDetail(
        environments=environments,
        playlists=playlists,
        songs=songs,
        audio_files=audio_files,
        match_links=match_links,
        source_discoveries=source_discoveries,
    ).execute(environment_id, playlist_id)
