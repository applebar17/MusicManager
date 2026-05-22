from collections import Counter

from music_manager_backend.application.dtos import PlaylistSummaryRead
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError


class ListEnvironmentPlaylists:
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

    def execute(self, environment_id: str) -> list[PlaylistSummaryRead]:
        if self.environments.get(environment_id) is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        status_by_song = {
            row.song_id: row.status
            for row in ListMatchReview(
                environments=self.environments,
                playlists=self.playlists,
                songs=self.songs,
                audio_files=self.audio_files,
                match_links=self.match_links,
            ).execute(environment_id)
        }
        summaries: list[PlaylistSummaryRead] = []
        for playlist in self.playlists.list_by_environment(environment_id):
            active_items = [item for item in playlist.items if item.remote_membership_active]
            inactive_items = [item for item in playlist.items if not item.remote_membership_active]
            statuses = Counter(
                status_by_song.get(item.song_id, "missing_audio") for item in active_items
            )
            summaries.append(
                PlaylistSummaryRead(
                    id=playlist.id,
                    name=playlist.display_name,
                    remote_playlist_id=playlist.remote_playlist_id,
                    active_item_count=len(active_items),
                    inactive_item_count=len(inactive_items),
                    matched_count=statuses["matched"],
                    missing_audio_count=statuses["missing_audio"],
                    ambiguous_count=statuses["ambiguous"],
                    manually_mapped_count=statuses["manually_mapped"],
                )
            )
        return summaries
