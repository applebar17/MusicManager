from music_manager_backend.application.dtos import MatchReviewRow
from music_manager_backend.application.use_cases.list_match_review import ListMatchReview
from music_manager_backend.application.use_cases.local_duplicate_linker import (
    link_local_duplicate_files,
)
from music_manager_backend.application.use_cases.matching_common import (
    active_audio_files_by_id,
    load_environment_songs,
)
from music_manager_backend.domain.entities import MatchLink
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class CreateManualMapping:
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

    def execute(self, environment_id: str, song_id: str, audio_file_id: str) -> MatchReviewRow:
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        if song_id not in environment_songs.song_ids:
            raise NotFoundError(f"Song not found in environment: {song_id}")

        active_files = active_audio_files_by_id(
            environment_id=environment_id, audio_files=self.audio_files
        )
        if audio_file_id not in active_files:
            raise ValidationError(f"Active audio file not found in environment: {audio_file_id}")

        song = self.songs.get(song_id)
        if song is None:
            raise NotFoundError(f"Song not found in environment: {song_id}")

        self.match_links.replace_for_song(
            MatchLink(
                song_id=song_id,
                audio_file_id=audio_file_id,
                method="manual",
                confidence=1.0,
                reviewed=True,
            )
        )
        link_local_duplicate_files(
            song=song,
            anchor_file=active_files[audio_file_id],
            active_files=active_files,
            match_links=self.match_links,
        )
        rows = ListMatchReview(
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
            audio_files=self.audio_files,
            match_links=self.match_links,
        ).execute(environment_id)
        for row in rows:
            if row.song_id == song_id:
                return row
        raise NotFoundError(f"Song not found in environment: {song_id}")
