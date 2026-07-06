import sqlite3
from pathlib import Path

import pytest

from music_manager_backend.application.use_cases.align_library import AlignLibraryFromEnvironment
from music_manager_backend.application.use_cases.scan_library import ScanLibrary
from music_manager_backend.domain.entities import AudioMetadata, MusicEnvironment
from music_manager_backend.domain.entities.library import (
    LibraryTrack,
    LibraryTrackStatus,
    MusicLibrary,
)
from music_manager_backend.infrastructure.filesystem import LocalAudioScanner
from music_manager_backend.infrastructure.persistence import (
    SqliteEnvironmentRepository,
    SqliteLibraryAlignmentRunRepository,
    SqliteLibraryRepository,
    SqliteLibraryTrackRepository,
)
from music_manager_backend.shared.errors import ValidationError


def test_scan_library_creates_tracks_and_marks_missing(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    library_root = tmp_path / "library"
    library_root.mkdir()
    track_path = library_root / "track.mp3"
    track_path.write_bytes(b"track")
    _save_library(sqlite_connection, library_root)
    use_case = _scan_use_case(sqlite_connection, _MetadataReader({"track.mp3": 180}))

    first = use_case.execute()
    track_path.unlink()
    second = use_case.execute()
    tracks = SqliteLibraryTrackRepository(sqlite_connection).list("default")

    assert first.track_count == 1
    assert second.track_count == 0
    assert second.missing_track_count == 1
    assert tracks[0].status == LibraryTrackStatus.MISSING


def test_alignment_copies_usb_only_song_with_original_filename(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    library_root, usb_root = _roots(tmp_path)
    source = usb_root / "Original Name.mp3"
    source.write_bytes(b"source")
    _save_library(sqlite_connection, library_root)
    _save_environment(sqlite_connection, usb_root)

    run = _align_use_case(
        sqlite_connection,
        _MetadataReader({"Original Name.mp3": 180}),
    ).execute("env_1")

    assert run.copied_count == 1
    assert run.reused_count == 0
    assert (library_root / "Original Name.mp3").read_bytes() == b"source"


def test_alignment_reuses_existing_identity_without_copying(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    library_root, usb_root = _roots(tmp_path)
    library_file = library_root / "library-track.mp3"
    usb_file = usb_root / "usb-track.mp3"
    library_file.write_bytes(b"library")
    usb_file.write_bytes(b"usb")
    _save_library(sqlite_connection, library_root)
    _save_environment(sqlite_connection, usb_root)
    track_repository = SqliteLibraryTrackRepository(sqlite_connection)
    track_repository.save(
        LibraryTrack(
            id="library_track_1",
            library_id="default",
            canonical_path=library_file,
            filename=library_file.name,
            size_bytes=7,
            modified_at=1.0,
            status=LibraryTrackStatus.ACTIVE,
            title="Shared Track",
            duration_seconds=180,
            normalized_title="shared track",
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )

    run = _align_use_case(
        sqlite_connection,
        _MetadataReader(
            {"library-track.mp3": 180, "usb-track.mp3": 180},
            titles={"library-track.mp3": "Shared Track", "usb-track.mp3": "Shared Track"},
        ),
    ).execute("env_1")

    assert run.reused_count == 1
    assert run.copied_count == 0
    assert not (library_root / "usb-track.mp3").exists()


def test_alignment_persists_collision_without_overwriting(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    library_root, usb_root = _roots(tmp_path)
    usb_file = usb_root / "candidate.mp3"
    usb_file.write_bytes(b"usb")
    _save_library(sqlite_connection, library_root)
    _save_environment(sqlite_connection, usb_root)
    track_repository = SqliteLibraryTrackRepository(sqlite_connection)
    for index in (1, 2):
        path = library_root / f"track-{index}.mp3"
        path.write_bytes(b"library")
        track_repository.save(
            LibraryTrack(
                id=f"library_track_{index}",
                library_id="default",
                canonical_path=path,
                filename=path.name,
                status=LibraryTrackStatus.ACTIVE,
                title="Collision",
                duration_seconds=180,
                normalized_title="collision",
                created_at="2026-07-06T10:00:00+00:00",
                updated_at="2026-07-06T10:00:00+00:00",
            )
        )

    run = _align_use_case(
        sqlite_connection,
        _MetadataReader(
            {
                "candidate.mp3": 180,
                "track-1.mp3": 180,
                "track-2.mp3": 180,
            },
            titles={
                "candidate.mp3": "Collision",
                "track-1.mp3": "Collision",
                "track-2.mp3": "Collision",
            },
        ),
    ).execute("env_1")

    assert run.skipped_collision_count == 1
    assert run.items[0].status == "skipped_collision"
    assert not (library_root / "candidate.mp3").exists()


def test_alignment_uses_filename_suffix_for_existing_target(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    library_root, usb_root = _roots(tmp_path)
    (library_root / "track.mp3").write_bytes(b"existing")
    (usb_root / "track.mp3").write_bytes(b"usb")
    _save_library(sqlite_connection, library_root)
    _save_environment(sqlite_connection, usb_root)

    run = _align_use_case(
        sqlite_connection,
        _MetadataReader(
            {str(library_root / "track.mp3"): 180, str(usb_root / "track.mp3"): 180},
            titles={
                str(library_root / "track.mp3"): "Existing Track",
                str(usb_root / "track.mp3"): "USB Track",
            },
        ),
    ).execute("env_1")

    assert run.copied_count == 1
    assert (library_root / "track (2).mp3").exists()


def test_alignment_rejects_overlapping_roots(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    library_root = root / "library"
    library_root.mkdir(parents=True)
    _save_library(sqlite_connection, library_root)
    _save_environment(sqlite_connection, root)

    with pytest.raises(ValidationError):
        _align_use_case(sqlite_connection, _MetadataReader({})).execute("env_1")


class _MetadataReader:
    def __init__(
        self,
        durations: dict[str, int],
        *,
        titles: dict[str, str] | None = None,
    ) -> None:
        self.durations = durations
        self.titles = titles or {}

    def read(self, path: Path) -> AudioMetadata:
        return AudioMetadata(
            title=self.titles.get(str(path), self.titles.get(path.name, path.stem)),
            duration_seconds=self.durations.get(str(path), self.durations.get(path.name)),
        )


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    library_root = tmp_path / "library"
    usb_root = tmp_path / "usb"
    library_root.mkdir()
    usb_root.mkdir()
    return library_root, usb_root


def _save_library(connection: sqlite3.Connection, root_path: Path) -> None:
    SqliteLibraryRepository(connection).save_default(
        MusicLibrary(
            id="default",
            root_path=root_path,
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )


def _save_environment(connection: sqlite3.Connection, root_path: Path) -> None:
    SqliteEnvironmentRepository(connection).save(
        MusicEnvironment(id="env_1", name="Gig USB", root_path=root_path)
    )


def _scan_use_case(
    connection: sqlite3.Connection,
    metadata_reader: _MetadataReader,
) -> ScanLibrary:
    return ScanLibrary(
        libraries=SqliteLibraryRepository(connection),
        library_tracks=SqliteLibraryTrackRepository(connection),
        metadata_reader=metadata_reader,
    )


def _align_use_case(
    connection: sqlite3.Connection,
    metadata_reader: _MetadataReader,
) -> AlignLibraryFromEnvironment:
    return AlignLibraryFromEnvironment(
        environments=SqliteEnvironmentRepository(connection),
        libraries=SqliteLibraryRepository(connection),
        library_tracks=SqliteLibraryTrackRepository(connection),
        alignment_runs=SqliteLibraryAlignmentRunRepository(connection),
        scanner_factory=LocalAudioScanner,
        metadata_reader=metadata_reader,
    )
