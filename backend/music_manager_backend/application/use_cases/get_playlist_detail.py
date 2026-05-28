from pathlib import Path

from music_manager_backend.application.dtos import PlaylistDetailRead, PlaylistItemRead
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
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
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links

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
            ).execute(environment_id)
        }
        items: list[PlaylistItemRead] = []
        for item in sorted(playlist.items, key=lambda value: (value.position, value.song_id)):
            song = self.songs.get(item.song_id)
            if song is None:
                continue
            review = review_by_song.get(item.song_id)
            accepted_audio_file_id = review.match.audio_file_id if review and review.match else None
            accepted_audio_filename = (
                _accepted_audio_filename(review.match.path) if review and review.match else None
            )
            accepted_audio_relative_path = (
                _accepted_audio_relative_path(review.match.path, environment.root_path)
                if review and review.match
                else None
            )
            accepted_audio_warnings = review.match.warnings if review and review.match else []
            items.append(
                PlaylistItemRead(
                    song_id=song.id,
                    position=item.position,
                    title=song.display_title,
                    artist=song.display_artist,
                    duration_seconds=song.duration_seconds,
                    remote_membership_active=item.remote_membership_active,
                    match_status=review.status if review is not None else "missing_audio",
                    accepted_audio_file_id=accepted_audio_file_id,
                    accepted_audio_filename=accepted_audio_filename,
                    accepted_audio_relative_path=accepted_audio_relative_path,
                    accepted_audio_warnings=accepted_audio_warnings,
                    playback_url=(
                        f"/environments/{environment_id}/playback/audio-files/"
                        f"{accepted_audio_file_id}"
                        if accepted_audio_file_id is not None
                        else None
                    ),
                )
            )
        return PlaylistDetailRead(
            id=playlist.id,
            environment_id=environment_id,
            name=playlist.display_name,
            remote_playlist_id=playlist.remote_playlist_id,
            active_item_count=sum(1 for item in playlist.items if item.remote_membership_active),
            inactive_item_count=sum(
                1 for item in playlist.items if not item.remote_membership_active
            ),
            items=items,
        )


def _accepted_audio_filename(path: str) -> str:
    return Path(path).name


def _accepted_audio_relative_path(path: str, root_path: Path) -> str:
    audio_path = Path(path)
    try:
        return audio_path.relative_to(root_path).as_posix()
    except ValueError:
        return audio_path.name
