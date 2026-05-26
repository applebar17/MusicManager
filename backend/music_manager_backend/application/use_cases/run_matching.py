from music_manager_backend.application.dtos import MatchingRunSummary
from music_manager_backend.application.use_cases.local_duplicate_linker import (
    link_local_duplicate_files,
)
from music_manager_backend.application.use_cases.match_link_selection import preferred_match_link
from music_manager_backend.application.use_cases.matching_common import (
    active_audio_files_by_id,
    load_environment_songs,
)
from music_manager_backend.domain.entities import MatchLink
from music_manager_backend.domain.services.match_scoring import (
    is_unique_high_confidence,
    score_song_files,
)
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
)


class RunMatching:
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

    def execute(self, environment_id: str) -> MatchingRunSummary:
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        active_files = active_audio_files_by_id(
            environment_id=environment_id, audio_files=self.audio_files
        )
        active_file_list = list(active_files.values())
        matched = 0
        missing = 0
        ambiguous = 0
        manual = 0

        for song in environment_songs.songs:
            accepted = preferred_match_link(self.match_links.list_by_song(song.id), active_files)
            if accepted is not None and accepted.reviewed:
                if accepted.method == "manual":
                    manual += 1
                else:
                    matched += 1
                link_local_duplicate_files(
                    song=song,
                    anchor_file=active_files[accepted.audio_file_id],
                    active_files=active_files,
                    match_links=self.match_links,
                )
                continue

            self.match_links.delete_automatic_by_song(song.id)
            candidates = score_song_files(
                song,
                active_file_list,
                playlist_names=environment_songs.playlist_names_by_song_id.get(song.id),
            )
            if is_unique_high_confidence(candidates):
                candidate = candidates[0]
                self.match_links.save(
                    MatchLink(
                        song_id=song.id,
                        audio_file_id=candidate.audio_file_id,
                        method=candidate.method,
                        confidence=candidate.confidence,
                    )
                )
                link_local_duplicate_files(
                    song=song,
                    anchor_file=active_files[candidate.audio_file_id],
                    active_files=active_files,
                    match_links=self.match_links,
                )
                matched += 1
            elif not candidates:
                missing += 1
            else:
                ambiguous += 1

        return MatchingRunSummary(
            environment_id=environment_id,
            total=len(environment_songs.songs),
            matched=matched,
            missing_audio=missing,
            ambiguous=ambiguous,
            manually_mapped=manual,
        )
