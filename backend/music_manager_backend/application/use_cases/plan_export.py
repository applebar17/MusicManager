from pathlib import Path

from music_manager_backend.domain.entities import (
    AudioFile,
    AudioFileStatus,
    ExportPlan,
    ExportPlanItem,
    MatchLink,
    Playlist,
    SongMaster,
)
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.domain.services.audio_quality import is_likely_preview_duration
from music_manager_backend.domain.services.export_layout import ExportLayout
from music_manager_backend.domain.services.match_scoring import score_song_files
from music_manager_backend.infrastructure.filesystem import read_export_manifest
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ExportPlanRepository,
    MatchLinkRepository,
    PlaylistRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError
from music_manager_backend.shared.ids import new_id


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
    ) -> None:
        self.environments = environments
        self.playlists = playlists
        self.songs = songs
        self.audio_files = audio_files
        self.match_links = match_links
        self.export_plans = export_plans

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
        layout = ExportLayout(environment)
        items: list[ExportPlanItem] = [
            ExportPlanItem(action=ExportAction.CREATE_FOLDER, target_path=layout.metadata_root),
            ExportPlanItem(action=ExportAction.CREATE_FOLDER, target_path=layout.deprecated_folder),
        ]
        planned_copy_targets: set[Path] = set()
        active_song_ids = _active_song_ids(all_playlists)

        for playlist in selected_playlists:
            folder = layout.playlist_folder(playlist)
            items.append(ExportPlanItem(action=ExportAction.CREATE_FOLDER, target_path=folder))
            for playlist_item in playlist.items:
                if not playlist_item.remote_membership_active:
                    continue
                song = self.songs.get(playlist_item.song_id)
                if song is None:
                    continue
                accepted_file = _accepted_audio_file(
                    song_id=song.id,
                    active_files=active_files,
                    match_links=self.match_links,
                )
                if accepted_file is not None:
                    if is_likely_preview_duration(accepted_file.duration_seconds):
                        items.append(
                            ExportPlanItem(
                                action=ExportAction.SKIP,
                                target_path=folder,
                                reason=_preview_skip_reason(accepted_file),
                            )
                        )
                        continue
                    item = _copy_or_keep_item(
                        folder=folder,
                        position=playlist_item.position,
                        song=song,
                        audio_file=accepted_file,
                        layout=layout,
                    )
                    planned_copy_targets.add(item.target_path)
                    items.append(item)
                    continue
                items.append(
                    ExportPlanItem(
                        action=ExportAction.SKIP,
                        target_path=folder,
                        reason=_skip_reason(song, list(active_files.values())),
                    )
                )

        items.extend(
            _stale_copy_items(
                selected_playlists=selected_playlists,
                layout=layout,
                planned_copy_targets=planned_copy_targets,
            )
        )
        items.extend(
            _deprecated_items(
                all_playlists=all_playlists,
                active_song_ids=active_song_ids,
                active_files=active_files,
                songs=self.songs,
                match_links=self.match_links,
                layout=layout,
            )
        )
        plan = ExportPlan(
            id=new_id("export_plan"),
            environment_id=environment_id,
            items=tuple(items),
        )
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


def _accepted_audio_file(
    *,
    song_id: str,
    active_files: dict[str, AudioFile],
    match_links: MatchLinkRepository,
) -> AudioFile | None:
    manual: list[MatchLink] = []
    automatic: list[MatchLink] = []
    for link in match_links.list_by_song(song_id):
        if link.audio_file_id not in active_files:
            continue
        if link.reviewed and link.method == "manual":
            manual.append(link)
        elif not link.reviewed:
            automatic.append(link)
    if manual:
        return active_files[manual[0].audio_file_id]
    if automatic:
        return active_files[automatic[0].audio_file_id]
    return None


def _skip_reason(song: SongMaster, active_files: list[AudioFile]) -> str:
    candidates = score_song_files(song, active_files)
    if candidates and all(item.method.startswith("likely_preview_") for item in candidates):
        return "likely preview download: local candidate is shorter than 1 minute"
    return "ambiguous audio match" if candidates else "missing audio"


def _preview_skip_reason(audio_file: AudioFile) -> str:
    duration = (
        f"{audio_file.duration_seconds}s"
        if audio_file.duration_seconds is not None
        else "under 1 minute"
    )
    return (
        f"likely preview download ({duration}): unmatch this audio and move it to deprecated "
        "before exporting"
    )


def _active_song_ids(playlists: list[Playlist]) -> set[str]:
    return {
        item.song_id
        for playlist in playlists
        for item in playlist.items
        if item.remote_membership_active
    }


def _stale_copy_items(
    *,
    selected_playlists: list[Playlist],
    layout: ExportLayout,
    planned_copy_targets: set[Path],
) -> list[ExportPlanItem]:
    playlist_folders = [layout.playlist_folder(playlist) for playlist in selected_playlists]
    if not playlist_folders:
        return []

    manifest = read_export_manifest(layout.environment.root_path)
    planned_resolved = {target.resolve(strict=False) for target in planned_copy_targets}
    items: list[ExportPlanItem] = []
    folder_roots = [folder.resolve(strict=False) for folder in playlist_folders]
    for path in sorted(manifest.targets):
        if path in planned_resolved:
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
) -> list[ExportPlanItem]:
    deprecated_song_ids = {
        item.song_id
        for playlist in all_playlists
        for item in playlist.items
        if not item.remote_membership_active and item.song_id not in active_song_ids
    }
    items: list[ExportPlanItem] = []
    for song_id in sorted(deprecated_song_ids):
        song = songs.get(song_id)
        if song is None:
            continue
        accepted_file = _accepted_audio_file(
            song_id=song_id,
            active_files=active_files,
            match_links=match_links,
        )
        if accepted_file is None:
            continue
        items.append(
            _deprecated_copy_or_keep_item(
                song=song,
                audio_file=accepted_file,
                layout=layout,
            )
        )
    return items


def _copy_or_keep_item(
    *,
    folder: Path,
    position: int,
    song: SongMaster,
    audio_file: AudioFile,
    layout: ExportLayout,
) -> ExportPlanItem:
    source = audio_file.path
    source_parent = source.parent.resolve(strict=False)
    folder_resolved = folder.resolve(strict=False)
    if source_parent == folder_resolved:
        return ExportPlanItem(
            action=ExportAction.KEEP_EXISTING,
            source_path=source,
            target_path=source,
            reason="matched audio is already in this playlist folder",
        )

    target = layout.track_target(
        folder=folder,
        position=position,
        song=song,
        audio_file=audio_file,
    )
    if target.exists() and target.is_file():
        return ExportPlanItem(
            action=ExportAction.KEEP_EXISTING,
            source_path=source,
            target_path=target,
            reason="matching filename already exists in this playlist folder",
        )

    return ExportPlanItem(
        action=ExportAction.COPY_FILE,
        source_path=source,
        target_path=target,
    )


def _deprecated_copy_or_keep_item(
    *,
    song: SongMaster,
    audio_file: AudioFile,
    layout: ExportLayout,
) -> ExportPlanItem:
    source = audio_file.path
    target = layout.deprecated_target(song=song, audio_file=audio_file)
    reason = "song no longer belongs to any active playlist"
    if source.resolve(strict=False).is_relative_to(layout.deprecated_folder.resolve(strict=False)):
        return ExportPlanItem(
            action=ExportAction.KEEP_EXISTING,
            source_path=source,
            target_path=source,
            reason=f"{reason}; already preserved in deprecated folder",
        )
    if target.exists() and target.is_file():
        return ExportPlanItem(
            action=ExportAction.KEEP_EXISTING,
            source_path=source,
            target_path=target,
            reason=f"{reason}; deprecated backup already exists",
        )
    return ExportPlanItem(
        action=ExportAction.PRESERVE_DEPRECATED,
        source_path=source,
        target_path=target,
        reason=reason,
    )
