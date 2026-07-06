import os
from collections.abc import Callable
from pathlib import Path

from music_manager_backend.application.dtos.library import LibraryRead, library_read
from music_manager_backend.domain.entities import AudioMetadata, DiscoveredAudioFile
from music_manager_backend.domain.entities.library import (
    LibraryTrack,
    LibraryTrackStatus,
)
from music_manager_backend.domain.services.title_normalizer import normalize_match_title
from music_manager_backend.infrastructure.filesystem.local_audio_scanner import (
    SUPPORTED_AUDIO_EXTENSIONS,
)
from music_manager_backend.infrastructure.filesystem.path_safety import validate_readable_directory
from music_manager_backend.ports.audio_metadata import AudioMetadataReader
from music_manager_backend.ports.repositories import (
    LibraryMetadataRepository,
    LibraryRepository,
    LibraryTrackRepository,
)
from music_manager_backend.shared.errors import NotFoundError
from music_manager_backend.shared.ids import new_id
from music_manager_backend.shared.time import utc_now_iso


class ScanLibrary:
    def __init__(
        self,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
        metadata_reader: AudioMetadataReader,
        library_metadata: LibraryMetadataRepository | None = None,
    ) -> None:
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.metadata_reader = metadata_reader
        self.library_metadata = library_metadata

    def execute(self) -> LibraryRead:
        library = self.libraries.get_default()
        if library is None:
            raise NotFoundError("Shared library is not configured.")
        scan_library(
            library_id=library.id,
            root_path=library.root_path,
            library_tracks=self.library_tracks,
            metadata_reader=self.metadata_reader,
        )
        return library_read(
            library,
            track_count=self.library_tracks.count(library.id),
            missing_track_count=self.library_tracks.count_by_status(
                library.id,
                LibraryTrackStatus.MISSING,
            ),
            metadata_asset_count=(
                self.library_metadata.count_assets(library.id)
                if self.library_metadata is not None
                else 0
            ),
            metadata_index_entry_count=(
                self.library_metadata.count_index_entries(library.id)
                if self.library_metadata is not None
                else 0
            ),
            last_metadata_imported_at=(
                self.library_metadata.last_imported_at(library.id)
                if self.library_metadata is not None
                else None
            ),
        )


def scan_library(
    *,
    library_id: str,
    root_path: Path,
    library_tracks: LibraryTrackRepository,
    metadata_reader: AudioMetadataReader,
) -> int:
    root = validate_readable_directory(root_path)
    now = utc_now_iso()
    discovered = _discover_flat(root, metadata_reader)
    discovered_by_path = {item.path: item for item in discovered}
    existing_active = library_tracks.list_by_status(library_id, LibraryTrackStatus.ACTIVE)

    for item in discovered:
        existing = library_tracks.get_by_canonical_path(library_id, item.path)
        library_tracks.save(_track_from_discovered(library_id, item, existing, now))

    missing_at = utc_now_iso()
    for track in existing_active:
        if track.canonical_path not in discovered_by_path:
            library_tracks.save(
                LibraryTrack(
                    id=track.id,
                    library_id=track.library_id,
                    canonical_path=track.canonical_path,
                    filename=track.filename,
                    size_bytes=track.size_bytes,
                    modified_at=track.modified_at,
                    status=LibraryTrackStatus.MISSING,
                    title=track.title,
                    artist=track.artist,
                    duration_seconds=track.duration_seconds,
                    normalized_title=track.normalized_title,
                    file_hash=track.file_hash,
                    created_at=track.created_at,
                    updated_at=missing_at,
                    first_seen_at=track.first_seen_at,
                    last_seen_at=track.last_seen_at,
                    missing_at=missing_at,
                )
            )
    return len(discovered)


def discover_audio_files_with_metadata(
    root_path: Path,
    scanner_factory: Callable[[Path], object],
    metadata_reader: AudioMetadataReader,
) -> list[DiscoveredAudioFile]:
    scanner = scanner_factory(root_path)
    scan = getattr(scanner, "scan")
    discovered = scan()
    return [_with_metadata(item, metadata_reader.read(item.path)) for item in discovered]


def _discover_flat(
    root: Path,
    metadata_reader: AudioMetadataReader,
) -> list[DiscoveredAudioFile]:
    files: list[DiscoveredAudioFile] = []
    for entry in _iter_directory(root):
        try:
            if not entry.is_file(follow_symlinks=False):
                continue
            path = Path(entry.path)
            if path.suffix.casefold() not in SUPPORTED_AUDIO_EXTENSIONS:
                continue
            stat = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        files.append(
            _with_metadata(
                DiscoveredAudioFile(
                    path=path,
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                ),
                metadata_reader.read(path),
            )
        )
    return files


def _track_from_discovered(
    library_id: str,
    item: DiscoveredAudioFile,
    existing: LibraryTrack | None,
    now: str,
) -> LibraryTrack:
    title = item.title or item.path.stem
    return LibraryTrack(
        id=existing.id if existing is not None else new_id("library_track"),
        library_id=library_id,
        canonical_path=item.path,
        filename=item.path.name,
        size_bytes=item.size_bytes,
        modified_at=item.modified_at,
        status=LibraryTrackStatus.ACTIVE,
        title=item.title,
        artist=item.artist,
        duration_seconds=item.duration_seconds,
        normalized_title=normalize_match_title(title),
        file_hash=existing.file_hash if existing is not None else None,
        created_at=existing.created_at if existing is not None else now,
        updated_at=now,
        first_seen_at=existing.first_seen_at if existing is not None else now,
        last_seen_at=now,
        missing_at=None,
    )


def _with_metadata(
    discovered_file: DiscoveredAudioFile,
    metadata: AudioMetadata,
) -> DiscoveredAudioFile:
    return DiscoveredAudioFile(
        path=discovered_file.path,
        size_bytes=discovered_file.size_bytes,
        modified_at=discovered_file.modified_at,
        title=metadata.title,
        artist=metadata.artist,
        album=metadata.album,
        duration_seconds=metadata.duration_seconds,
        bpm=metadata.bpm,
        key=metadata.key,
        comment=metadata.comment,
        raw_metadata=metadata.raw,
    )


def _iter_directory(directory: Path) -> list[os.DirEntry[str]]:
    try:
        with os.scandir(directory) as entries:
            return sorted(entries, key=lambda entry: entry.name.casefold())
    except OSError:
        return []
