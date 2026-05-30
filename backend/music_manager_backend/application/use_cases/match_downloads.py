from pathlib import Path

from music_manager_backend.application.dtos import (
    DownloadMatchRunResultRead,
    DownloadMatchSummaryRead,
    ScanSummaryRead,
)
from music_manager_backend.application.use_cases.audio_file_area import path_is_inside
from music_manager_backend.application.use_cases.local_duplicate_linker import (
    link_local_duplicate_files,
)
from music_manager_backend.application.use_cases.match_link_selection import (
    preferred_match_link,
)
from music_manager_backend.application.use_cases.matching_common import (
    active_audio_files_by_id,
    load_environment_songs,
)
from music_manager_backend.application.use_cases.scan_environment import (
    ScannerFactory,
    ScanEnvironment,
)
from music_manager_backend.domain.entities import MatchLink
from music_manager_backend.domain.services.match_scoring import (
    is_unique_high_confidence,
    score_song_files,
)
from music_manager_backend.infrastructure.filesystem import validate_readable_directory
from music_manager_backend.ports.audio_metadata import AudioMetadataReader
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    ScanRunRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class MatchDownloads:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
        scan_runs: ScanRunRepository,
        scanner_factory: ScannerFactory,
        metadata_reader: AudioMetadataReader,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links
        self.scan_runs = scan_runs
        self.scanner_factory = scanner_factory
        self.metadata_reader = metadata_reader

    def execute(self, environment_id: str) -> DownloadMatchRunResultRead:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        if environment.download_path is None:
            raise ValidationError(
                "Configure a download folder before matching downloads.",
                code="download_path_required",
            )

        download_path = validate_readable_directory(environment.download_path)
        scan = ScanEnvironment(
            environments=self.environments,
            audio_files=self.audio_files,
            scan_runs=self.scan_runs,
            scanner_factory=self.scanner_factory,
            metadata_reader=self.metadata_reader,
        ).execute_roots(environment_id, [download_path])

        matching = self._run_download_matching(
            environment_id=environment_id,
            download_path=download_path,
        )
        return DownloadMatchRunResultRead(
            environment_id=environment_id,
            download_path=str(download_path),
            scan=ScanSummaryRead(
                scan_run_id=scan.scan_run_id,
                environment_id=scan.environment_id,
                added=scan.added,
                changed=scan.changed,
                removed=scan.removed,
                moved=scan.moved,
                unchanged=scan.unchanged,
                total_active=scan.total_active,
            ),
            matching=matching,
        )

    def _run_download_matching(
        self,
        *,
        environment_id: str,
        download_path: Path,
    ) -> DownloadMatchSummaryRead:
        environment_songs = load_environment_songs(
            environment_id=environment_id,
            environments=self.environments,
            playlists=self.playlists,
            songs=self.songs,
        )
        active_files = active_audio_files_by_id(
            environment_id=environment_id,
            audio_files=self.audio_files,
        )
        active_download_files = [
            audio_file
            for audio_file in active_files.values()
            if path_is_inside(audio_file.path, download_path)
        ]
        download_file_ids = {
            audio_file.id
            for audio_file in self.audio_files.list_by_environment(environment_id)
            if path_is_inside(audio_file.path, download_path)
        }

        checked = 0
        matched = 0
        missing = 0
        ambiguous = 0
        preserved_reviewed = 0

        for song in environment_songs.songs:
            links = self.match_links.list_by_song(song.id)
            accepted = preferred_match_link(links, active_files)
            if accepted is not None and accepted.reviewed:
                preserved_reviewed += 1
                continue

            checked += 1
            self.match_links.delete_automatic_by_song_audio_files(song.id, download_file_ids)
            candidates = score_song_files(
                song,
                active_download_files,
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

        return DownloadMatchSummaryRead(
            checked=checked,
            matched=matched,
            missing_audio=missing,
            ambiguous=ambiguous,
            preserved_reviewed=preserved_reviewed,
        )
