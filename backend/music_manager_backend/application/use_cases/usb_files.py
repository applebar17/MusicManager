from __future__ import annotations

import os
import shutil
from dataclasses import replace
from pathlib import Path

from music_manager_backend.application.dtos import (
    UsbAudioFileBatchQuarantineResult,
    UsbFileRead,
    UsbMatchedSongRead,
    UsbSongCandidateRead,
)
from music_manager_backend.application.use_cases.matching_common import (
    active_audio_files_by_id,
    load_environment_songs,
)
from music_manager_backend.domain.entities import (
    AudioFile,
    AudioFileStatus,
    MatchLink,
    MatchStatus,
    MusicEnvironment,
    SongMaster,
)
from music_manager_backend.domain.services.audio_quality import audio_warnings
from music_manager_backend.domain.services.export_layout import ExportLayout
from music_manager_backend.domain.services.filename_sanitizer import sanitize_path_part
from music_manager_backend.domain.services.match_scoring import score_song_file, score_song_files
from music_manager_backend.domain.services.title_normalizer import normalize_title
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError
from music_manager_backend.shared.time import utc_now_iso


class ListUsbFiles:
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

    def execute(self, environment_id: str) -> list[UsbFileRead]:
        environment = _environment_or_raise(self.environments, environment_id)
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
        matched_by_audio_file_id = _matched_songs_by_audio_file_id(
            songs=environment_songs.songs,
            playlist_names_by_song_id=environment_songs.playlist_names_by_song_id,
            active_files=active_files,
            match_links=self.match_links,
        )
        return [
            _usb_file_read(
                environment=environment,
                audio_file=audio_file,
                matched_song=matched_by_audio_file_id.get(audio_file.id),
            )
            for audio_file in active_files.values()
        ]


class ListUsbMatchCandidates:
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

    def execute(
        self,
        environment_id: str,
        *,
        audio_file_id: str,
        query: str = "",
    ) -> list[UsbSongCandidateRead]:
        _environment_or_raise(self.environments, environment_id)
        audio_file = self.audio_files.get(audio_file_id)
        if audio_file is None or audio_file.environment_id != environment_id:
            raise NotFoundError(f"Audio file not found: {audio_file_id}")
        if audio_file.status != AudioFileStatus.ACTIVE:
            raise ValidationError(f"Audio file is not active: {audio_file_id}")

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
        active_file_list = list(active_files.values())
        normalized_query = normalize_title(query)
        candidates: list[UsbSongCandidateRead] = []

        for song in environment_songs.songs:
            if _accepted_link(self.match_links.list_by_song(song.id), active_files) is not None:
                continue

            playlist_names = environment_songs.playlist_names_by_song_id.get(song.id, set())
            global_candidates = score_song_files(
                song,
                active_file_list,
                playlist_names=playlist_names,
            )
            selected_candidate = score_song_file(song, audio_file)
            matches_query = _song_matches_query(song, playlist_names, normalized_query)
            if selected_candidate is None and not matches_query:
                continue
            if not normalized_query and selected_candidate is None:
                continue

            candidates.append(
                UsbSongCandidateRead(
                    song_id=song.id,
                    title=song.display_title,
                    artist=song.display_artist,
                    duration_seconds=song.duration_seconds,
                    playlists=sorted(playlist_names),
                    status=(
                        MatchStatus.AMBIGUOUS.value
                        if global_candidates
                        else MatchStatus.MISSING_AUDIO.value
                    ),
                    method=selected_candidate.method if selected_candidate is not None else None,
                    confidence=(
                        selected_candidate.confidence if selected_candidate is not None else 0.0
                    ),
                )
            )

        return sorted(
            candidates,
            key=lambda item: (-item.confidence, item.title.casefold(), item.song_id),
        )[:50]


class QuarantineUsbAudioFile:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files
        self.match_links = match_links

    def execute(self, environment_id: str, audio_file_id: str) -> UsbFileRead:
        environment = _environment_or_raise(self.environments, environment_id)
        audio_file = self.audio_files.get(audio_file_id)
        audio_file = _quarantine_audio_file_or_raise(environment_id, audio_file_id, audio_file)

        source = _validated_quarantine_source(environment, audio_file)
        target = _next_available_deprecated_path(environment, source, reserved_targets=set())
        removed_audio_file = _move_to_deprecated(
            audio_file=audio_file,
            target=target,
            audio_files=self.audio_files,
            match_links=self.match_links,
        )
        return _usb_file_read(
            environment=environment,
            audio_file=removed_audio_file,
            matched_song=None,
        )


class QuarantineUsbAudioFiles:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files
        self.match_links = match_links

    def execute(
        self,
        environment_id: str,
        *,
        audio_file_ids: list[str],
        confirmation: str,
    ) -> UsbAudioFileBatchQuarantineResult:
        if confirmation != "delete":
            raise ValidationError(
                'Type "delete" to move selected files to deprecated.',
                code="delete_confirmation_required",
            )
        selected_ids = list(dict.fromkeys(audio_file_ids))
        if not selected_ids:
            raise ValidationError(
                "Select at least one audio file to move to deprecated.",
                code="no_audio_files_selected",
            )

        environment = _environment_or_raise(self.environments, environment_id)
        reserved_targets: set[Path] = set()
        planned_items: list[tuple[AudioFile, Path]] = []
        for audio_file_id in selected_ids:
            audio_file = self.audio_files.get(audio_file_id)
            audio_file = _quarantine_audio_file_or_raise(
                environment_id,
                audio_file_id,
                audio_file,
            )
            source = _validated_quarantine_source(environment, audio_file)
            target = _next_available_deprecated_path(
                environment,
                source,
                reserved_targets=reserved_targets,
            )
            reserved_targets.add(target.resolve(strict=False))
            planned_items.append((audio_file, target))

        removed_files = [
            _move_to_deprecated(
                audio_file=audio_file,
                target=target,
                audio_files=self.audio_files,
                match_links=self.match_links,
            )
            for audio_file, target in planned_items
        ]
        return UsbAudioFileBatchQuarantineResult(
            removed=len(removed_files),
            files=[
                _usb_file_read(
                    environment=environment,
                    audio_file=audio_file,
                    matched_song=None,
                )
                for audio_file in removed_files
            ],
        )


def _environment_or_raise(
    environments: EnvironmentRepository,
    environment_id: str,
) -> MusicEnvironment:
    environment = environments.get(environment_id)
    if environment is None:
        raise NotFoundError(f"Environment not found: {environment_id}")
    return environment


def _quarantine_audio_file_or_raise(
    environment_id: str,
    audio_file_id: str,
    audio_file: AudioFile | None,
) -> AudioFile:
    if audio_file is None or audio_file.environment_id != environment_id:
        raise NotFoundError(f"Audio file not found: {audio_file_id}")
    if audio_file.status != AudioFileStatus.ACTIVE:
        raise ValidationError(f"Audio file is not active: {audio_file_id}")
    return audio_file


def _matched_songs_by_audio_file_id(
    *,
    songs: list[SongMaster],
    playlist_names_by_song_id: dict[str, set[str]],
    active_files: dict[str, AudioFile],
    match_links: MatchLinkRepository,
) -> dict[str, UsbMatchedSongRead]:
    matched: dict[str, UsbMatchedSongRead] = {}
    for song in songs:
        accepted = _accepted_link(match_links.list_by_song(song.id), active_files)
        if accepted is None:
            continue
        matched.setdefault(
            accepted.audio_file_id,
            UsbMatchedSongRead(
                song_id=song.id,
                title=song.display_title,
                artist=song.display_artist,
                duration_seconds=song.duration_seconds,
                playlists=sorted(playlist_names_by_song_id.get(song.id, set())),
                method=accepted.method,
                confidence=accepted.confidence,
                reviewed=accepted.reviewed,
            ),
        )
    return matched


def _accepted_link(
    links: list[MatchLink],
    active_files: dict[str, AudioFile],
) -> MatchLink | None:
    manual = [
        link
        for link in links
        if link.reviewed and link.method == "manual" and link.audio_file_id in active_files
    ]
    if manual:
        return manual[0]
    automatic = [
        link
        for link in links
        if not link.reviewed and link.audio_file_id in active_files
    ]
    return automatic[0] if automatic else None


def _usb_file_read(
    *,
    environment: MusicEnvironment,
    audio_file: AudioFile,
    matched_song: UsbMatchedSongRead | None,
) -> UsbFileRead:
    relative_path = _relative_audio_path(environment, audio_file.path)
    return UsbFileRead(
        audio_file_id=audio_file.id,
        environment_id=audio_file.environment_id,
        path=str(audio_file.path),
        relative_path=relative_path.as_posix(),
        folder_parts=[] if relative_path.parent == Path(".") else list(relative_path.parent.parts),
        filename=relative_path.name,
        audio_status=audio_file.status.value,
        match_status="matched" if matched_song is not None else "unmatched",
        warnings=audio_warnings(audio_file.duration_seconds),
        title=audio_file.title,
        artist=audio_file.artist,
        album=audio_file.album,
        duration_seconds=audio_file.duration_seconds,
        bpm=audio_file.bpm,
        key=audio_file.key,
        comment=audio_file.comment,
        size_bytes=audio_file.size_bytes,
        modified_at=audio_file.modified_at,
        matched_song=matched_song,
    )


def _relative_audio_path(environment: MusicEnvironment, path: Path) -> Path:
    root = environment.root_path.resolve(strict=False)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValidationError(f"Audio file path is outside environment root: {path}")
    return resolved.relative_to(root)


def _song_matches_query(
    song: SongMaster,
    playlist_names: set[str],
    normalized_query: str,
) -> bool:
    if not normalized_query:
        return False
    haystack = [
        normalize_title(song.display_title),
        normalize_title(song.display_artist or ""),
        normalize_title(song.id),
        *(normalize_title(name) for name in playlist_names),
    ]
    return any(normalized_query in value for value in haystack if value)


def _validated_quarantine_source(
    environment: MusicEnvironment,
    audio_file: AudioFile,
) -> Path:
    try:
        root = environment.root_path.resolve(strict=True)
    except FileNotFoundError as exc:
        message = f"Environment root path does not exist: {environment.root_path}"
        raise ValidationError(message) from exc

    source_path = audio_file.path
    if not source_path.exists():
        raise NotFoundError(f"Audio file no longer exists on disk: {source_path}")
    source = source_path.resolve(strict=True)
    if not source.is_relative_to(root):
        raise ValidationError(f"Audio file path is outside environment root: {source_path}")
    if not source.is_file():
        raise ValidationError(f"Audio file path is not a file: {source_path}")
    if not os.access(source, os.R_OK):
        raise ValidationError(f"Audio file path is not readable: {source_path}")
    metadata_root = ExportLayout(environment).metadata_root.resolve(strict=False)
    if source.is_relative_to(metadata_root):
        raise ValidationError(f"Audio file path is already inside app metadata: {source_path}")
    return source


def _move_to_deprecated(
    *,
    audio_file: AudioFile,
    target: Path,
    audio_files: AudioFileRepository,
    match_links: MatchLinkRepository,
) -> AudioFile:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(audio_file.path), str(target))

    removed_audio_file = replace(
        audio_file,
        status=AudioFileStatus.REMOVED,
        removed_at=utc_now_iso(),
    )
    match_links.delete_by_audio_file(audio_file.id)
    audio_files.save(removed_audio_file)
    return removed_audio_file


def _next_available_deprecated_path(
    environment: MusicEnvironment,
    source: Path,
    *,
    reserved_targets: set[Path],
) -> Path:
    layout = ExportLayout(environment)
    stem = sanitize_path_part(source.stem, fallback="audio")
    suffix = source.suffix
    deprecated_root = layout.deprecated_folder
    candidate = deprecated_root / f"{stem}{suffix}"
    index = 2
    while candidate.exists() or candidate.resolve(strict=False) in reserved_targets:
        candidate = deprecated_root / f"{stem} ({index}){suffix}"
        index += 1
    resolved_root = deprecated_root.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)
    if not resolved_candidate.is_relative_to(resolved_root):
        raise ValidationError(f"Deprecated target path is outside metadata folder: {candidate}")
    return candidate
