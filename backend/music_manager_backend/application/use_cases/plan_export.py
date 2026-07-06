from pathlib import Path

from music_manager_backend.application.use_cases.library_matching import (
    active_library_tracks_by_id,
    preferred_library_link,
)
from music_manager_backend.application.use_cases.match_link_selection import (
    active_match_links,
    preferred_match_link,
)
from music_manager_backend.application.use_cases.export_plan_validation import (
    validate_export_plan,
)
from music_manager_backend.domain.entities import (
    AudioFile,
    AudioFileStatus,
    ExportPlan,
    ExportPlanItem,
    LibraryTrack,
    Playlist,
    SongMaster,
)
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.domain.services.audio_quality import is_likely_preview_duration
from music_manager_backend.domain.services.export_layout import ExportLayout
from music_manager_backend.domain.services.title_normalizer import normalize_match_title
from music_manager_backend.infrastructure.filesystem import read_export_manifest
from music_manager_backend.ports.audio_metadata import AudioMetadataReader
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ExportPlanRepository,
    LibraryRepository,
    LibraryTrackRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongLibraryLinkRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError
from music_manager_backend.shared.ids import new_id

_AUDIO_EXTENSIONS = {".aiff", ".flac", ".m4a", ".mp3", ".wav"}
_DEPRECATED_DURATION_TOLERANCE_RATIO = 0.03


class PlanExport:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        playlists: PlaylistRepository,
        songs: SongRepository,
        audio_files: AudioFileRepository,
        match_links: MatchLinkRepository,
        export_plans: ExportPlanRepository,
        metadata_reader: AudioMetadataReader,
        libraries: LibraryRepository | None = None,
        library_tracks: LibraryTrackRepository | None = None,
        song_library_links: SongLibraryLinkRepository | None = None,
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links
        self.export_plans = export_plans
        self.metadata_reader = metadata_reader
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.song_library_links = song_library_links

    def execute(self, environment_id: str, playlist_ids: list[str] | None = None) -> ExportPlan:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        all_playlists = self.playlists.list_by_environment(environment_id)
        selected_playlists = _select_playlists(all_playlists, playlist_ids)
        active_files = {
            item.id: item
            for item in self.audio_files.list_by_environment(
                environment_id, status=AudioFileStatus.ACTIVE
            )
        }
        library = self.libraries.get_default() if self.libraries is not None else None
        active_library_tracks = (
            active_library_tracks_by_id(library.id, self.library_tracks)
            if library is not None and self.library_tracks is not None
            else {}
        )
        use_library_sources = (
            library is not None
            and self.library_tracks is not None
            and self.song_library_links is not None
        )
        layout = ExportLayout(environment)
        items: list[ExportPlanItem] = []
        for folder in (layout.metadata_root, layout.deprecated_folder):
            folder_item = _folder_item_if_missing(folder)
            if folder_item is not None:
                items.append(folder_item)
        planned_copy_targets: set[Path] = set()
        planned_removal_targets: set[Path] = set()
        active_song_ids = _active_song_ids(all_playlists)

        for playlist in selected_playlists:
            folder = layout.playlist_folder(playlist)
            folder_item = _folder_item_if_missing(folder)
            if folder_item is not None:
                items.append(folder_item)
            for playlist_item in playlist.items:
                if not playlist_item.is_active:
                    continue
                song = self.songs.get(playlist_item.song_id)
                if song is None:
                    continue
                linked_files = _linked_audio_files(
                    song_id=song.id,
                    active_files=active_files,
                    match_links=self.match_links,
                )
                if use_library_sources:
                    library_track = _linked_library_track(
                        song_id=song.id,
                        active_tracks=active_library_tracks,
                        song_library_links=self.song_library_links,
                    )
                    if library_track is None:
                        items.append(
                            ExportPlanItem(
                                action=ExportAction.SKIP,
                                target_path=folder,
                                reason=f"No active library mapping for {song.display_title}",
                            )
                        )
                        continue

                    existing_file = _preferred_audio_file_in_folder(
                        folder=folder,
                        linked_files=linked_files,
                    )
                    if existing_file is not None:
                        target = existing_file.path
                        item = ExportPlanItem(
                            action=ExportAction.KEEP_EXISTING,
                            source_path=target,
                            target_path=target,
                            reason="linked file already exists in playlist folder",
                        )
                    else:
                        target, item = _copy_or_keep_library_item(
                            folder=folder,
                            library_track=library_track,
                            layout=layout,
                        )
                    planned_copy_targets.add(target)
                    if item is not None:
                        items.append(item)
                    duplicate_items = _duplicate_copy_items(
                        folder=folder,
                        linked_files=linked_files,
                        kept_target=target,
                        song=song,
                    )
                    planned_removal_targets.update(
                        item.target_path for item in duplicate_items
                    )
                    items.extend(duplicate_items)
                    continue

                if not linked_files:
                    items.append(
                        ExportPlanItem(
                            action=ExportAction.SKIP,
                            target_path=folder,
                            reason=f"No accepted audio file for {song.display_title}",
                        )
                    )
                    continue

                accepted_file = _preferred_audio_file_for_folder(
                    folder=folder,
                    linked_files=linked_files,
                )
                if accepted_file is None:
                    items.append(
                        ExportPlanItem(
                            action=ExportAction.SKIP,
                            target_path=folder,
                            reason=_preview_skip_reason(linked_files),
                        )
                    )
                    continue

                target, item = _copy_or_keep_item(
                    folder=folder,
                    position=playlist_item.position,
                    song=song,
                    audio_file=accepted_file,
                    layout=layout,
                )
                planned_copy_targets.add(target)
                if item is not None:
                    items.append(item)
                duplicate_items = _duplicate_copy_items(
                    folder=folder,
                    linked_files=linked_files,
                    kept_target=target,
                    song=song,
                )
                planned_removal_targets.update(
                    item.target_path for item in duplicate_items
                )
                items.extend(duplicate_items)

        items.extend(
            _deprecated_items(
                all_playlists=all_playlists,
                active_song_ids=active_song_ids,
                active_files=active_files,
                songs=self.songs,
                match_links=self.match_links,
                layout=layout,
                metadata_reader=self.metadata_reader,
            )
        )
        items.extend(
            _stale_copy_items(
                selected_playlists=selected_playlists,
                layout=layout,
                planned_copy_targets=planned_copy_targets,
                planned_removal_targets=planned_removal_targets,
            )
        )
        plan = ExportPlan(
            id=new_id("export_plan"),
            environment_id=environment_id,
            items=tuple(items),
        )
        plan = validate_export_plan(environment, plan)
        self.export_plans.save(plan)
        return plan


def _select_playlists(
    playlists: list[Playlist], playlist_ids: list[str] | None
) -> list[Playlist]:
    if not playlist_ids:
        return playlists
    by_id = {playlist.id: playlist for playlist in playlists}
    missing = [playlist_id for playlist_id in playlist_ids if playlist_id not in by_id]
    if missing:
        raise NotFoundError(f"Playlist not found in environment: {missing[0]}")
    return [by_id[playlist_id] for playlist_id in playlist_ids]


def _linked_audio_files(
    *,
    song_id: str,
    active_files: dict[str, AudioFile],
    match_links: MatchLinkRepository,
) -> list[AudioFile]:
    links = match_links.list_by_song(song_id)
    preferred = preferred_match_link(links, active_files)
    ordered_links = []
    if preferred is not None:
        ordered_links.append(preferred)
    ordered_links.extend(
        link
        for link in active_match_links(links, active_files)
        if preferred is None or link.audio_file_id != preferred.audio_file_id
    )
    seen: set[str] = set()
    files: list[AudioFile] = []
    for link in ordered_links:
        if link.audio_file_id in seen:
            continue
        seen.add(link.audio_file_id)
        files.append(active_files[link.audio_file_id])
    return files


def _linked_library_track(
    *,
    song_id: str,
    active_tracks: dict[str, LibraryTrack],
    song_library_links: SongLibraryLinkRepository,
) -> LibraryTrack | None:
    link = preferred_library_link(song_library_links.list_by_song(song_id), active_tracks)
    if link is None:
        return None
    return active_tracks.get(link.library_track_id)


def _preferred_audio_file_in_folder(
    *,
    folder: Path,
    linked_files: list[AudioFile],
) -> AudioFile | None:
    folder_resolved = folder.resolve(strict=False)
    for audio_file in _exportable_audio_files(linked_files):
        if audio_file.path.parent.resolve(strict=False) == folder_resolved:
            return audio_file
    return None


def _preferred_audio_file_for_folder(
    *,
    folder: Path,
    linked_files: list[AudioFile],
) -> AudioFile | None:
    exportable = _exportable_audio_files(linked_files)
    folder_resolved = folder.resolve(strict=False)
    for audio_file in exportable:
        if audio_file.path.parent.resolve(strict=False) == folder_resolved:
            return audio_file
    return exportable[0] if exportable else None


def _best_exportable_audio_file(linked_files: list[AudioFile]) -> AudioFile | None:
    exportable = _exportable_audio_files(linked_files)
    return exportable[0] if exportable else None


def _exportable_audio_files(linked_files: list[AudioFile]) -> list[AudioFile]:
    return [
        audio_file
        for audio_file in linked_files
        if not is_likely_preview_duration(audio_file.duration_seconds)
    ]


def _active_song_ids(playlists: list[Playlist]) -> set[str]:
    return {
        item.song_id
        for playlist in playlists
        for item in playlist.items
        if item.is_active
    }


def _stale_copy_items(
    *,
    selected_playlists: list[Playlist],
    layout: ExportLayout,
    planned_copy_targets: set[Path],
    planned_removal_targets: set[Path],
) -> list[ExportPlanItem]:
    playlist_folders = [layout.playlist_folder(playlist) for playlist in selected_playlists]
    if not playlist_folders:
        return []

    manifest = read_export_manifest(layout.environment.root_path)
    planned_resolved = {target.resolve(strict=False) for target in planned_copy_targets}
    planned_removal_resolved = {
        target.resolve(strict=False) for target in planned_removal_targets
    }
    items: list[ExportPlanItem] = []
    folder_roots = [folder.resolve(strict=False) for folder in playlist_folders]
    for path in sorted(manifest.targets):
        if path in planned_resolved:
            continue
        if path in planned_removal_resolved:
            continue
        if not any(path.is_relative_to(folder) for folder in folder_roots):
            continue
        if not path.exists() or not path.is_file():
            continue
        items.append(
            ExportPlanItem(
                action=ExportAction.REMOVE_STALE_COPY,
                target_path=path,
                reason="stale app-owned export copy",
            )
        )
    return items


def _deprecated_items(
    *,
    all_playlists: list[Playlist],
    active_song_ids: set[str],
    active_files: dict[str, AudioFile],
    songs: SongRepository,
    match_links: MatchLinkRepository,
    layout: ExportLayout,
    metadata_reader: AudioMetadataReader,
) -> list[ExportPlanItem]:
    deprecated_song_ids = {
        item.song_id
        for playlist in all_playlists
        for item in playlist.items
        if item.is_removed_history and item.song_id not in active_song_ids
    }
    items: list[ExportPlanItem] = []
    for song_id in sorted(deprecated_song_ids):
        song = songs.get(song_id)
        if song is None:
            continue
        linked_files = _linked_audio_files(
            song_id=song_id,
            active_files=active_files,
            match_links=match_links,
        )
        accepted_file = _best_exportable_audio_file(linked_files)
        if accepted_file is None:
            continue
        item = _deprecated_copy_item_if_missing(
            song=song,
            audio_file=accepted_file,
            layout=layout,
            metadata_reader=metadata_reader,
        )
        if item is not None:
            items.append(item)
    return items


def _folder_item_if_missing(folder: Path) -> ExportPlanItem | None:
    if folder.exists():
        return None
    return ExportPlanItem(action=ExportAction.CREATE_FOLDER, target_path=folder)


def _copy_or_keep_item(
    *,
    folder: Path,
    position: int,
    song: SongMaster,
    audio_file: AudioFile,
    layout: ExportLayout,
) -> tuple[Path, ExportPlanItem | None]:
    source = audio_file.path
    source_parent = source.parent.resolve(strict=False)
    folder_resolved = folder.resolve(strict=False)
    if source_parent == folder_resolved:
        return (
            source,
            ExportPlanItem(
                action=ExportAction.KEEP_EXISTING,
                source_path=source,
                target_path=source,
                reason="linked file already exists in playlist folder",
            ),
        )

    target = layout.track_target(
        folder=folder,
        position=position,
        song=song,
        audio_file=audio_file,
    )
    if target.exists() and target.is_file():
        return (
            target,
            ExportPlanItem(
                action=ExportAction.KEEP_EXISTING,
                source_path=source,
                target_path=target,
                reason="target file already exists",
            ),
        )

    return (
        target,
        ExportPlanItem(
            action=ExportAction.COPY_FILE,
            source_path=source,
            target_path=target,
        ),
    )


def _copy_or_keep_library_item(
    *,
    folder: Path,
    library_track: LibraryTrack,
    layout: ExportLayout,
) -> tuple[Path, ExportPlanItem | None]:
    source = library_track.canonical_path
    target = layout.track_target_from_path(folder=folder, source_path=source)
    if target.exists() and target.is_file():
        return (
            target,
            ExportPlanItem(
                action=ExportAction.KEEP_EXISTING,
                source_path=source,
                target_path=target,
                reason="target file already exists",
            ),
        )
    return (
        target,
        ExportPlanItem(
            action=ExportAction.COPY_FILE,
            source_path=source,
            target_path=target,
        ),
    )


def _duplicate_copy_items(
    *,
    folder: Path,
    linked_files: list[AudioFile],
    kept_target: Path,
    song: SongMaster,
) -> list[ExportPlanItem]:
    folder_resolved = folder.resolve(strict=False)
    kept_resolved = kept_target.resolve(strict=False)
    items: list[ExportPlanItem] = []
    seen: set[Path] = set()
    for audio_file in linked_files:
        path = audio_file.path
        resolved_path = path.resolve(strict=False)
        if resolved_path == kept_resolved:
            continue
        if path.parent.resolve(strict=False) != folder_resolved:
            continue
        if not path.exists() or not path.is_file():
            continue
        if resolved_path in seen:
            continue
        seen.add(resolved_path)
        items.append(
            ExportPlanItem(
                action=ExportAction.REMOVE_DUPLICATE_COPY,
                target_path=path,
                reason=(
                    f"duplicate local copy of {song.display_title}; "
                    f"keeping {kept_target.name}"
                ),
            )
        )
    return items


def _preview_skip_reason(linked_files: list[AudioFile]) -> str:
    if len(linked_files) == 1:
        return "Matched audio file is likely a preview download under 60 seconds"
    return "Only matched local copies are likely preview downloads under 60 seconds"


def _deprecated_copy_item_if_missing(
    *,
    song: SongMaster,
    audio_file: AudioFile,
    layout: ExportLayout,
    metadata_reader: AudioMetadataReader,
) -> ExportPlanItem | None:
    source = audio_file.path
    target = layout.deprecated_target(song=song, audio_file=audio_file)
    reason = "song no longer belongs to any active playlist"
    if source.resolve(strict=False).is_relative_to(layout.deprecated_folder.resolve(strict=False)):
        return None
    if target.exists() and target.is_file():
        return None
    if _deprecated_equivalent_exists(
        song=song,
        audio_file=audio_file,
        deprecated_folder=layout.deprecated_folder,
        metadata_reader=metadata_reader,
    ):
        return None
    return ExportPlanItem(
        action=ExportAction.PRESERVE_DEPRECATED,
        source_path=source,
        target_path=target,
        reason=reason,
    )


def _deprecated_equivalent_exists(
    *,
    song: SongMaster,
    audio_file: AudioFile,
    deprecated_folder: Path,
    metadata_reader: AudioMetadataReader,
) -> bool:
    reference_title = normalize_match_title(song.display_title)
    reference_duration = song.duration_seconds or audio_file.duration_seconds
    if not reference_title or reference_duration is None:
        return False
    for candidate in _deprecated_audio_files(deprecated_folder):
        metadata = metadata_reader.read(candidate)
        candidate_title = normalize_match_title(metadata.title or candidate.stem)
        if candidate_title != reference_title:
            continue
        if _duration_within_deprecated_tolerance(
            reference_duration,
            metadata.duration_seconds,
        ):
            return True
    return False


def _deprecated_audio_files(deprecated_folder: Path) -> list[Path]:
    if not deprecated_folder.exists() or not deprecated_folder.is_dir():
        return []
    return sorted(
        (
            path
            for path in deprecated_folder.rglob("*")
            if path.is_file() and path.suffix.casefold() in _AUDIO_EXTENSIONS
        ),
        key=lambda path: path.as_posix().casefold(),
    )


def _duration_within_deprecated_tolerance(
    reference_duration: int,
    candidate_duration: int | None,
) -> bool:
    if candidate_duration is None:
        return False
    tolerance = reference_duration * _DEPRECATED_DURATION_TOLERANCE_RATIO
    return abs(reference_duration - candidate_duration) <= tolerance
