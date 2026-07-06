import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from music_manager_backend.application.dtos.library import (
    LibraryMetadataImportRunRead,
    library_metadata_import_run_read,
)
from music_manager_backend.domain.entities.library import (
    LibraryAlignmentItemStatus,
    LibraryMetadataAsset,
    LibraryMetadataAssetStatus,
    LibraryMetadataImportRun,
    LibraryMetadataImportRunStatus,
    LibraryMetadataIndexEntry,
    LibraryTrack,
    LibraryTrackStatus,
)
from music_manager_backend.domain.services.export_layout import EXPORT_METADATA_FOLDER_NAME
from music_manager_backend.domain.services.title_normalizer import normalize_match_title
from music_manager_backend.infrastructure.filesystem.local_audio_scanner import (
    IGNORED_DIRECTORY_NAMES,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from music_manager_backend.infrastructure.filesystem.path_safety import validate_readable_directory
from music_manager_backend.ports.repositories import (
    EnvironmentRepository,
    LibraryAlignmentRunRepository,
    LibraryMetadataRepository,
    LibraryRepository,
    LibraryTrackRepository,
)
from music_manager_backend.shared.errors import NotFoundError, ValidationError
from music_manager_backend.shared.ids import new_id
from music_manager_backend.shared.time import utc_now_iso

TRACKS_JSON_PROVIDER = "tracks_json"
SERATO_PROVIDER = "serato"
UNKNOWN_PROVIDER = "unknown"


class ImportLibraryMetadataFromEnvironment:
    def __init__(
        self,
        environments: EnvironmentRepository,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
        alignment_runs: LibraryAlignmentRunRepository,
        metadata_repository: LibraryMetadataRepository,
    ) -> None:
        self.environments = environments
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.alignment_runs = alignment_runs
        self.metadata_repository = metadata_repository

    def execute(
        self,
        environment_id: str,
        *,
        alignment_run_id: str | None = None,
    ) -> LibraryMetadataImportRunRead:
        library = self.libraries.get_default()
        if library is None:
            raise NotFoundError("Shared library is not configured.")
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        library_root = validate_readable_directory(library.root_path)
        environment_root = validate_readable_directory(environment.root_path)
        _reject_overlapping_roots(library_root, environment_root)

        run_id = new_id("library_metadata_import")
        started_at = utc_now_iso()
        asset_root = library_root / EXPORT_METADATA_FOLDER_NAME / "metadata-assets" / run_id
        index_root = library_root / EXPORT_METADATA_FOLDER_NAME / "metadata-index"
        source_to_track = self._source_to_track_map(alignment_run_id)
        active_tracks = self.library_tracks.list_by_status(library.id, LibraryTrackStatus.ACTIVE)
        discoveries = _discover_metadata_assets(environment_root)
        assets: list[LibraryMetadataAsset] = []
        entries: list[LibraryMetadataIndexEntry] = []

        for discovery in discoveries:
            imported_at = utc_now_iso()
            asset_id = new_id("library_metadata_asset")
            try:
                stored_path = _copy_asset(discovery, environment_root, asset_root)
                asset = LibraryMetadataAsset(
                    id=asset_id,
                    run_id=run_id,
                    library_id=library.id,
                    provider=discovery.provider,
                    asset_type=discovery.asset_type,
                    source_path=discovery.path,
                    stored_path=stored_path,
                    size_bytes=_asset_size(discovery.path),
                    modified_at=_modified_at(discovery.path),
                    imported_at=imported_at,
                    status=LibraryMetadataAssetStatus.COPIED,
                )
            except OSError as exc:
                assets.append(
                    LibraryMetadataAsset(
                        id=asset_id,
                        run_id=run_id,
                        library_id=library.id,
                        provider=discovery.provider,
                        asset_type=discovery.asset_type,
                        source_path=discovery.path,
                        stored_path=None,
                        size_bytes=0,
                        modified_at=0.0,
                        imported_at=imported_at,
                        status=LibraryMetadataAssetStatus.SKIPPED_ERROR,
                        error_code="copy_failed",
                        error_message=str(exc),
                    )
                )
                continue

            assets.append(asset)
            if discovery.provider == TRACKS_JSON_PROVIDER and discovery.path.is_file():
                entries.extend(
                    _tracks_json_entries(
                        library_id=library.id,
                        source_asset_id=asset.id,
                        source_path=discovery.path,
                        imported_at=imported_at,
                        environment_root=environment_root,
                        source_to_track=source_to_track,
                        active_tracks=active_tracks,
                        library_tracks=self.library_tracks,
                    )
                )

        _write_tracks_index(index_root, entries)
        error_count = sum(1 for asset in assets if asset.status == LibraryMetadataAssetStatus.SKIPPED_ERROR)
        status = (
            LibraryMetadataImportRunStatus.COMPLETED_WITH_ISSUES
            if error_count
            else LibraryMetadataImportRunStatus.COMPLETED
        )
        run = LibraryMetadataImportRun(
            id=run_id,
            library_id=library.id,
            environment_id=environment_id,
            alignment_run_id=alignment_run_id,
            status=status,
            started_at=started_at,
            finished_at=utc_now_iso(),
            asset_count=sum(1 for asset in assets if asset.status == LibraryMetadataAssetStatus.COPIED),
            index_entry_count=len(entries),
            error_count=error_count,
        )
        asset_tuple = tuple(assets)
        entry_tuple = tuple(entries)
        self.metadata_repository.save_import_run(run, asset_tuple, entry_tuple)
        return library_metadata_import_run_read(run, asset_tuple, entry_tuple)

    def latest(self) -> LibraryMetadataImportRunRead | None:
        library = self.libraries.get_default()
        if library is None:
            return None
        latest = self.metadata_repository.latest(library.id)
        if latest is None:
            return None
        run, assets, entries = latest
        return library_metadata_import_run_read(run, assets, entries)

    def _source_to_track_map(self, alignment_run_id: str | None) -> dict[Path, str]:
        if alignment_run_id is None:
            return {}
        run_bundle = self.alignment_runs.get(alignment_run_id)
        if run_bundle is None:
            return {}
        _run, items = run_bundle
        return {
            item.source_path.resolve(strict=False): item.library_track_id
            for item in items
            if item.library_track_id is not None
            and item.status
            in (
                LibraryAlignmentItemStatus.COPIED,
                LibraryAlignmentItemStatus.REUSED,
                LibraryAlignmentItemStatus.WARNING_IDENTITY_INCOMPLETE,
            )
        }


class GetLatestLibraryMetadataImportRun:
    def __init__(
        self,
        libraries: LibraryRepository,
        metadata_repository: LibraryMetadataRepository,
    ) -> None:
        self.libraries = libraries
        self.metadata_repository = metadata_repository

    def execute(self) -> LibraryMetadataImportRunRead | None:
        library = self.libraries.get_default()
        if library is None:
            return None
        latest = self.metadata_repository.latest(library.id)
        if latest is None:
            return None
        run, assets, entries = latest
        return library_metadata_import_run_read(run, assets, entries)


@dataclass(frozen=True)
class _MetadataDiscovery:
    path: Path
    provider: str
    asset_type: str


def _discover_metadata_assets(root: Path) -> list[_MetadataDiscovery]:
    discoveries: list[_MetadataDiscovery] = []
    for directory, dirnames, filenames in os.walk(root):
        directory_path = Path(directory)
        if directory_path.name in IGNORED_DIRECTORY_NAMES:
            dirnames[:] = []
            continue

        pruned: list[str] = []
        for dirname in sorted(dirnames, key=str.casefold):
            child = directory_path / dirname
            if dirname in IGNORED_DIRECTORY_NAMES:
                continue
            if dirname == "_Serato":
                discoveries.append(
                    _MetadataDiscovery(child, SERATO_PROVIDER, "serato_folder")
                )
                continue
            if _folder_has_no_audio(child) and not _folder_contains_tracks_json(child):
                discoveries.append(
                    _MetadataDiscovery(child, UNKNOWN_PROVIDER, "unknown_folder")
                )
                continue
            pruned.append(dirname)
        dirnames[:] = pruned

        for filename in sorted(filenames, key=str.casefold):
            path = directory_path / filename
            if path.suffix.casefold() in SUPPORTED_AUDIO_EXTENSIONS:
                continue
            if filename.casefold() == "tracks.json":
                discoveries.append(
                    _MetadataDiscovery(path, TRACKS_JSON_PROVIDER, "tracks_json")
                )
            else:
                discoveries.append(
                    _MetadataDiscovery(path, UNKNOWN_PROVIDER, "unknown_file")
                )
    return discoveries


def _folder_has_no_audio(path: Path) -> bool:
    for directory, dirnames, filenames in os.walk(path):
        directory_path = Path(directory)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in IGNORED_DIRECTORY_NAMES
        ]
        if directory_path.name in IGNORED_DIRECTORY_NAMES:
            dirnames[:] = []
            continue
        for filename in filenames:
            if Path(filename).suffix.casefold() in SUPPORTED_AUDIO_EXTENSIONS:
                return False
    return True


def _folder_contains_tracks_json(path: Path) -> bool:
    for child in path.rglob("tracks.json"):
        if child.is_file():
            return True
    return False


def _copy_asset(discovery: _MetadataDiscovery, root: Path, asset_root: Path) -> Path:
    relative = discovery.path.relative_to(root)
    target = asset_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if discovery.path.is_dir():
        shutil.copytree(discovery.path, target, dirs_exist_ok=False)
        return target
    shutil.copy2(discovery.path, target)
    return target


def _tracks_json_entries(
    *,
    library_id: str,
    source_asset_id: str,
    source_path: Path,
    imported_at: str,
    environment_root: Path,
    source_to_track: dict[Path, str],
    active_tracks: list[LibraryTrack],
    library_tracks: LibraryTrackRepository,
) -> list[LibraryMetadataIndexEntry]:
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    entries: list[LibraryMetadataIndexEntry] = []
    for index, item in enumerate(_entry_payloads(payload)):
        payload_json = json.dumps(item, sort_keys=True, ensure_ascii=False)
        entry_key = _entry_key(source_path, index, item)
        track_id = _associated_track_id(
            item,
            source_path=source_path,
            environment_root=environment_root,
            source_to_track=source_to_track,
            active_tracks=active_tracks,
            library_id=library_id,
            library_tracks=library_tracks,
        )
        entries.append(
            LibraryMetadataIndexEntry(
                id=new_id("library_metadata_entry"),
                library_id=library_id,
                provider=TRACKS_JSON_PROVIDER,
                source_asset_id=source_asset_id,
                source_path=source_path,
                library_track_id=track_id,
                entry_key=entry_key,
                payload_json=payload_json,
                imported_at=imported_at,
            )
        )
    return entries


def _entry_payloads(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("tracks", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        if payload and all(isinstance(value, dict) for value in payload.values()):
            return list(payload.values())
        return [payload]
    return [payload]


def _entry_key(source_path: Path, index: int, payload: object) -> str:
    if isinstance(payload, dict):
        for key in ("id", "track_id", "uuid", "persistent_id", "path", "filename", "file"):
            value = payload.get(key)
            if isinstance(value, str | int | float) and str(value).strip():
                return f"{key}:{value}"
    return f"{source_path.as_posix()}#{index}"


def _associated_track_id(
    payload: object,
    *,
    source_path: Path,
    environment_root: Path,
    source_to_track: dict[Path, str],
    active_tracks: list[LibraryTrack],
    library_id: str,
    library_tracks: LibraryTrackRepository,
) -> str | None:
    if not isinstance(payload, dict):
        return None

    for referenced_path in _referenced_paths(payload, source_path, environment_root):
        mapped = source_to_track.get(referenced_path.resolve(strict=False))
        if mapped is not None:
            return mapped

    referenced_names = {path.name.casefold() for path in _referenced_paths(payload, source_path, environment_root)}
    if referenced_names:
        matches = [track for track in active_tracks if track.filename.casefold() in referenced_names]
        if len(matches) == 1:
            return matches[0].id

    title = _text_value(payload, "title", "name", "track_title")
    duration = _int_value(payload, "duration_seconds", "duration", "length", "duration_ms")
    if title is None or duration is None:
        return None
    matches = library_tracks.get_by_identity(library_id, normalize_match_title(title), duration)
    return matches[0].id if len(matches) == 1 else None


def _referenced_paths(payload: dict[object, object], source_path: Path, root: Path) -> list[Path]:
    paths: list[Path] = []
    for key in ("path", "file", "filename", "location", "url"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        candidate = Path(value)
        if not candidate.is_absolute():
            paths.append((source_path.parent / candidate).resolve(strict=False))
            paths.append((root / candidate).resolve(strict=False))
        else:
            paths.append(candidate.resolve(strict=False))
    return paths


def _text_value(payload: dict[object, object], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _int_value(payload: dict[object, object], *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int | float):
            number = int(round(float(value)))
            if key == "duration_ms":
                number = int(round(number / 1000))
            return number if number > 0 else None
        if isinstance(value, str):
            try:
                number = int(round(float(value)))
            except ValueError:
                continue
            if key == "duration_ms":
                number = int(round(number / 1000))
            return number if number > 0 else None
    return None


def _write_tracks_index(index_root: Path, entries: list[LibraryMetadataIndexEntry]) -> None:
    index_root.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "entry_key": entry.entry_key,
            "library_track_id": entry.library_track_id,
            "provider": entry.provider,
            "source_path": str(entry.source_path),
            "payload": json.loads(entry.payload_json),
            "imported_at": entry.imported_at,
        }
        for entry in entries
    ]
    (index_root / "tracks.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def _asset_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def _modified_at(path: Path) -> float:
    return path.stat().st_mtime


def _reject_overlapping_roots(library_root: Path, environment_root: Path) -> None:
    library_resolved = library_root.resolve(strict=True)
    environment_resolved = environment_root.resolve(strict=True)
    if library_resolved == environment_resolved:
        raise ValidationError("Library root and environment root must be different folders.")
    if library_resolved.is_relative_to(environment_resolved):
        raise ValidationError("Library root cannot be inside the environment root.")
    if environment_resolved.is_relative_to(library_resolved):
        raise ValidationError("Environment root cannot be inside the library root.")
