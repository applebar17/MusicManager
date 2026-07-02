from collections import Counter

from music_manager_backend.application.dtos import EnvironmentOverviewRead
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.domain.entities import AudioFileStatus
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError


class GetEnvironmentOverview:
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

    def execute(self, environment_id: str) -> EnvironmentOverviewRead:
        if self.environments.get(environment_id) is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        playlists = self.playlists.list_by_environment(environment_id)
        active_item_count = sum(
            1 for playlist in playlists for item in playlist.items if item.is_active
        )
        inactive_item_count = sum(
            1
            for playlist in playlists
            for item in playlist.items
            if item.is_removed_history
        )
        unique_song_ids = {
            item.song_id for playlist in playlists for item in playlist.items if item.is_active
        }
        active_audio_files = self.audio_files.list_by_environment(
            environment_id, status=AudioFileStatus.ACTIVE
        )
        removed_audio_files = self.audio_files.list_by_environment(
            environment_id, status=AudioFileStatus.REMOVED
        )
        unmanaged_audio_files = self.audio_files.list_unmanaged_active_by_environment(
            environment_id
        )
        statuses = Counter(
            row.status
            for row in ListMatchReview(
                environments=self.environments,
                playlists=self.playlists,
                songs=self.songs,
                audio_files=self.audio_files,
                match_links=self.match_links,
            ).execute(environment_id)
        )
        return EnvironmentOverviewRead(
            environment_id=environment_id,
            playlist_count=len(playlists),
            active_playlist_item_count=active_item_count,
            inactive_playlist_item_count=inactive_item_count,
            unique_song_count=len(unique_song_ids),
            active_audio_file_count=len(active_audio_files),
            removed_audio_file_count=len(removed_audio_files),
            unmanaged_audio_file_count=len(unmanaged_audio_files),
            matched_count=statuses["matched"],
            missing_audio_count=statuses["missing_audio"],
            ambiguous_count=statuses["ambiguous"],
            manually_mapped_count=statuses["manually_mapped"],
        )
