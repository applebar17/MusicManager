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
        items: list[ExportPlanItem] = []
        for folder in (layout.metadata_root, layout.deprecated_folder):
            folder_item = _folder_item_if_missing(folder)
            if folder_item is not None:
                items.append(folder_item)
        planned_copy_targets: set[Path] = set()
        active_song_ids = _active_song_ids(all_playlists)

        for playlist in selected_playlists:
            folder = layout.playlist_folder(playlist)
            folder_item = _folder_item_if_missing(folder)
            if folder_item is not None:
                items.append(folder_item)
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
                        continue
                    target, item = _copy_item_if_missing(
                        folder=folder,
                        position=playlist_item.position,
                        song=song,
                        audio_file=accepted_file,
                        layout=layout,
                    )
                    planned_copy_targets.add(target)
                    if item is not None:
                        items.append(item)

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
        items.extend(
            _stale_copy_items(
                selected_playlists=selected_playlists,
                layout=layout,
                planned_copy_targets=planned_copy_targets,
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
        item = _deprecated_copy_item_if_missing(
            song=song,
            audio_file=accepted_file,
            layout=layout,
        )
        if item is not None:
            items.append(item)
    return items


def _folder_item_if_missing(folder: Path) -> ExportPlanItem | None:
    if folder.exists():
        return None
    return ExportPlanItem(action=ExportAction.CREATE_FOLDER, target_path=folder)


def _copy_item_if_missing(
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
        return source, None

    target = layout.track_target(
        folder=folder,
        position=position,
        song=song,
        audio_file=audio_file,
    )
    if target.exists() and target.is_file():
        return target, None

    return (
        target,
        ExportPlanItem(
            action=ExportAction.COPY_FILE,
            source_path=source,
            target_path=target,
        ),
    )


def _deprecated_copy_item_if_missing(
    *,
    song: SongMaster,
    audio_file: AudioFile,
    layout: ExportLayout,
) -> ExportPlanItem | None:
    source = audio_file.path
    target = layout.deprecated_target(song=song, audio_file=audio_file)
    reason = "song no longer belongs to any active playlist"
    if source.resolve(strict=False).is_relative_to(layout.deprecated_folder.resolve(strict=False)):
        return None
    if target.exists() and target.is_file():
        return None
    return ExportPlanItem(
        action=ExportAction.PRESERVE_DEPRECATED,
        source_path=source,
        target_path=target,
        reason=reason,
    )
