import sqlite3
from pathlib import Path

import pytest

from music_manager_backend.application.use_cases.apply_export_plan import ApplyExportPlan
from music_manager_backend.domain.entities import (
    AudioFile,
    ExportApplyItemStatus,
    ExportApplyRunStatus,
    ExportPlan,
    ExportPlanItem,
    LibraryTrack,
    LibraryTrackStatus,
    MusicEnvironment,
    MusicLibrary,
)
from music_manager_backend.domain.entities.export_plan import ExportAction
from music_manager_backend.infrastructure.filesystem import update_export_manifest
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteExportApplyRunRepository,
    SqliteExportPlanRepository,
    SqliteLibraryRepository,
    SqliteLibraryTrackRepository,
)
from music_manager_backend.shared.errors import ValidationError


def test_apply_export_plan_writes_expected_files_and_results(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "track.mp3", b"playlist audio")
    stale = root / "Set" / "stale.mp3"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")
    duplicate = root / "Set" / "duplicate.mp3"
    duplicate.write_bytes(b"duplicate")
    update_export_manifest(
        root_path=root,
        add_targets={duplicate, stale},
        remove_targets=set(),
    )
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.audio_files.save(_audio_file("file_duplicate", duplicate))
    plan = ExportPlan(
        id="plan_1",
        environment_id="env_1",
        items=(
            ExportPlanItem(
                action=ExportAction.CREATE_FOLDER,
                target_path=root / "_music_manager",
            ),
            ExportPlanItem(
                action=ExportAction.CREATE_FOLDER,
                target_path=root / "Set",
            ),
            ExportPlanItem(
                action=ExportAction.COPY_FILE,
                source_path=source,
                target_path=root / "Set" / "001 - Track.mp3",
            ),
            ExportPlanItem(
                action=ExportAction.WRITE_TRACKS_JSON,
                target_path=root / "Set" / "tracks.json",
                metadata_payload_json='[{"filename": "001 - Track.mp3"}]',
            ),
            ExportPlanItem(
                action=ExportAction.KEEP_EXISTING,
                source_path=source,
                target_path=source,
                reason="already present",
            ),
            ExportPlanItem(
                action=ExportAction.REMOVE_STALE_COPY,
                target_path=stale,
            ),
            ExportPlanItem(
                action=ExportAction.REMOVE_DUPLICATE_COPY,
                target_path=duplicate,
                reason="duplicate local copy",
            ),
            ExportPlanItem(
                action=ExportAction.SKIP,
                target_path=root / "Set",
                reason="missing audio",
            ),
        ),
    )
    repositories.export_plans.save(plan)

    apply_run = _apply_export_plan(repositories).execute("env_1", "plan_1")

    copied = root / "Set" / "001 - Track.mp3"
    tracks_json = root / "Set" / "tracks.json"
    assert copied.read_bytes() == b"playlist audio"
    assert tracks_json.read_text(encoding="utf-8") == '[{"filename": "001 - Track.mp3"}]\n'
    assert not stale.exists()
    assert not duplicate.exists()
    assert source.exists()
    assert apply_run.status == ExportApplyRunStatus.COMPLETED
    assert [item.status for item in apply_run.item_results] == [
        ExportApplyItemStatus.SUCCEEDED,
        ExportApplyItemStatus.SUCCEEDED,
        ExportApplyItemStatus.SUCCEEDED,
        ExportApplyItemStatus.SUCCEEDED,
        ExportApplyItemStatus.SUCCEEDED,
        ExportApplyItemStatus.SUCCEEDED,
        ExportApplyItemStatus.SUCCEEDED,
        ExportApplyItemStatus.SKIPPED,
    ]
    assert repositories.apply_runs.get(apply_run.id) == apply_run


def test_apply_export_plan_records_partial_failures_and_continues(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "track.mp3", b"audio")
    repositories.audio_files.save(_audio_file("file_1", source))
    missing_source = root / "missing.mp3"
    good_target = root / "Set" / "good.mp3"
    plan = ExportPlan(
        id="plan_1",
        environment_id="env_1",
        items=(
            ExportPlanItem(
                action=ExportAction.COPY_FILE,
                source_path=missing_source,
                target_path=root / "Set" / "bad.mp3",
            ),
            ExportPlanItem(
                action=ExportAction.COPY_FILE,
                source_path=source,
                target_path=good_target,
            ),
        ),
    )
    repositories.export_plans.save(plan)

    apply_run = _apply_export_plan(repositories).execute("env_1", "plan_1")

    assert apply_run.status == ExportApplyRunStatus.COMPLETED_WITH_FAILURES
    assert apply_run.item_results[0].status == ExportApplyItemStatus.FAILED
    assert apply_run.item_results[1].status == ExportApplyItemStatus.SUCCEEDED
    assert good_target.read_bytes() == b"audio"


def test_apply_export_plan_allows_active_library_track_source(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    library_source = tmp_path / "library" / "track.mp3"
    library_source.parent.mkdir()
    library_source.write_bytes(b"library audio")
    _seed_library_track(repositories, library_source)
    target = root / "Set" / "track.mp3"
    repositories.export_plans.save(
        ExportPlan(
            id="plan_1",
            environment_id="env_1",
            items=(
                ExportPlanItem(
                    action=ExportAction.COPY_FILE,
                    source_path=library_source,
                    target_path=target,
                ),
            ),
        )
    )

    apply_run = _apply_export_plan(repositories).execute("env_1", "plan_1")

    assert target.read_bytes() == b"library audio"
    assert apply_run.status == ExportApplyRunStatus.COMPLETED
    assert apply_run.item_results[0].status == ExportApplyItemStatus.SUCCEEDED


def test_apply_export_plan_rejects_missing_library_track_source(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    library_source = tmp_path / "library" / "track.mp3"
    library_source.parent.mkdir()
    library_source.write_bytes(b"library audio")
    _seed_library_track(repositories, library_source, status=LibraryTrackStatus.MISSING)
    target = root / "Set" / "track.mp3"
    repositories.export_plans.save(
        ExportPlan(
            id="plan_1",
            environment_id="env_1",
            items=(
                ExportPlanItem(
                    action=ExportAction.COPY_FILE,
                    source_path=library_source,
                    target_path=target,
                ),
            ),
        )
    )

    apply_run = _apply_export_plan(repositories).execute("env_1", "plan_1")

    assert not target.exists()
    assert apply_run.status == ExportApplyRunStatus.FAILED
    assert apply_run.item_results[0].status == ExportApplyItemStatus.FAILED
    assert apply_run.item_results[0].error_code == "validation_error"
    assert "approved active export source" in (apply_run.item_results[0].error_message or "")


def test_apply_export_plan_locks_plan_after_apply(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = _source_file(root, "track.mp3", b"fresh audio")
    target = root / "Set" / "track.mp3"
    stale_target = root / "Set" / "gone.mp3"
    update_export_manifest(root_path=root, add_targets={stale_target}, remove_targets=set())
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.export_plans.save(
        ExportPlan(
            id="plan_1",
            environment_id="env_1",
            items=(
                ExportPlanItem(
                    action=ExportAction.CREATE_FOLDER,
                    target_path=target.parent,
                ),
                ExportPlanItem(
                    action=ExportAction.COPY_FILE,
                    source_path=source,
                    target_path=target,
                ),
                ExportPlanItem(
                    action=ExportAction.REMOVE_STALE_COPY,
                    target_path=stale_target,
                ),
            ),
        )
    )

    _apply_export_plan(repositories).execute("env_1", "plan_1")
    target.write_bytes(b"older managed copy")

    with pytest.raises(ValidationError) as exc_info:
        _apply_export_plan(repositories).execute("env_1", "plan_1")

    assert exc_info.value.code == "export_plan_locked"
    assert target.read_bytes() == b"older managed copy"


def test_apply_export_plan_preserves_deprecated_before_removing_stale_source(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = root / "Old Set" / "old.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"old audio")
    deprecated = root / "_music_manager" / "_deprecated" / "old.mp3"
    update_export_manifest(root_path=root, add_targets={source}, remove_targets=set())
    repositories.audio_files.save(_audio_file("file_1", source))
    repositories.export_plans.save(
        ExportPlan(
            id="plan_1",
            environment_id="env_1",
            items=(
                ExportPlanItem(
                    action=ExportAction.PRESERVE_DEPRECATED,
                    source_path=source,
                    target_path=deprecated,
                ),
                ExportPlanItem(
                    action=ExportAction.REMOVE_STALE_COPY,
                    target_path=source,
                ),
            ),
        )
    )

    apply_run = _apply_export_plan(repositories).execute("env_1", "plan_1")

    assert deprecated.read_bytes() == b"old audio"
    assert not source.exists()
    assert apply_run.status == ExportApplyRunStatus.COMPLETED
    assert [item.status for item in apply_run.item_results] == [
        ExportApplyItemStatus.SUCCEEDED,
        ExportApplyItemStatus.SUCCEEDED,
    ]


def test_apply_export_plan_blocks_stale_removal_when_deprecated_preserve_fails(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = root / "Old Set" / "old.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"old audio")
    deprecated = root / "_music_manager" / "_deprecated" / "old.mp3"
    update_export_manifest(root_path=root, add_targets={source}, remove_targets=set())
    repositories.export_plans.save(
        ExportPlan(
            id="plan_1",
            environment_id="env_1",
            items=(
                ExportPlanItem(
                    action=ExportAction.PRESERVE_DEPRECATED,
                    source_path=source,
                    target_path=deprecated,
                ),
                ExportPlanItem(
                    action=ExportAction.REMOVE_STALE_COPY,
                    target_path=source,
                ),
            ),
        )
    )

    apply_run = _apply_export_plan(repositories).execute("env_1", "plan_1")

    assert source.exists()
    assert not deprecated.exists()
    assert apply_run.status == ExportApplyRunStatus.FAILED
    assert [item.status for item in apply_run.item_results] == [
        ExportApplyItemStatus.FAILED,
        ExportApplyItemStatus.FAILED,
    ]
    assert apply_run.item_results[1].error_code == "stale_removal_blocked"


def test_apply_export_plan_blocks_stale_removal_when_active_copy_fails(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    source = root / "Old Set" / "shared.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"shared audio")
    active_target = root / "Current Set" / "shared.mp3"
    update_export_manifest(root_path=root, add_targets={source}, remove_targets=set())
    repositories.export_plans.save(
        ExportPlan(
            id="plan_1",
            environment_id="env_1",
            items=(
                ExportPlanItem(
                    action=ExportAction.COPY_FILE,
                    source_path=source,
                    target_path=active_target,
                ),
                ExportPlanItem(
                    action=ExportAction.REMOVE_STALE_COPY,
                    target_path=source,
                ),
            ),
        )
    )

    apply_run = _apply_export_plan(repositories).execute("env_1", "plan_1")

    assert source.exists()
    assert not active_target.exists()
    assert apply_run.status == ExportApplyRunStatus.FAILED
    assert [item.status for item in apply_run.item_results] == [
        ExportApplyItemStatus.FAILED,
        ExportApplyItemStatus.FAILED,
    ]
    assert apply_run.item_results[1].error_code == "stale_removal_blocked"


def test_apply_export_plan_rejects_wrong_environment(
    sqlite_connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repositories = _repositories(sqlite_connection)
    root = _seed_environment(repositories, tmp_path)
    repositories.environments.save(
        MusicEnvironment(id="env_2", name="Other", root_path=tmp_path / "other")
    )
    repositories.export_plans.save(
        ExportPlan(
            id="plan_1",
            environment_id="env_1",
            items=(
                ExportPlanItem(
                    action=ExportAction.CREATE_FOLDER,
                    target_path=root / "_music_manager",
                ),
            ),
        )
    )

    with pytest.raises(ValidationError):
        _apply_export_plan(repositories).execute("env_2", "plan_1")


class _Repositories:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.environments = SqliteEnvironmentRepository(connection)
        self.audio_files = SqliteAudioFileRepository(connection)
        self.export_plans = SqliteExportPlanRepository(connection)
        self.apply_runs = SqliteExportApplyRunRepository(connection)
        self.libraries = SqliteLibraryRepository(connection)
        self.library_tracks = SqliteLibraryTrackRepository(connection)


def _repositories(connection: sqlite3.Connection) -> _Repositories:
    return _Repositories(connection)


def _seed_environment(repositories: _Repositories, tmp_path: Path) -> Path:
    root = tmp_path / "usb"
    root.mkdir()
    repositories.environments.save(MusicEnvironment(id="env_1", name="USB", root_path=root))
    return root


def _source_file(root: Path, filename: str, content: bytes) -> Path:
    source = root / "source" / filename
    source.parent.mkdir()
    source.write_bytes(content)
    return source


def _seed_library_track(
    repositories: _Repositories,
    source: Path,
    *,
    status: LibraryTrackStatus = LibraryTrackStatus.ACTIVE,
) -> None:
    repositories.libraries.save_default(
        MusicLibrary(
            id="default",
            root_path=source.parent,
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )
    repositories.library_tracks.save(
        LibraryTrack(
            id="library_track_1",
            library_id="default",
            canonical_path=source,
            filename=source.name,
            status=status,
            created_at="2026-07-06T10:00:00+00:00",
            updated_at="2026-07-06T10:00:00+00:00",
        )
    )


def _audio_file(audio_file_id: str, path: Path) -> AudioFile:
    return AudioFile(
        id=audio_file_id,
        environment_id="env_1",
        path=path,
        size_bytes=path.stat().st_size,
        modified_at=path.stat().st_mtime,
    )


def _apply_export_plan(repositories: _Repositories) -> ApplyExportPlan:
    return ApplyExportPlan(
        environments=repositories.environments,
        audio_files=repositories.audio_files,
        libraries=repositories.libraries,
        library_tracks=repositories.library_tracks,
        export_plans=repositories.export_plans,
        apply_runs=repositories.apply_runs,
    )
