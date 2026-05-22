from pathlib import Path

import pytest

from music_manager_backend.domain.entities import MusicEnvironment
from music_manager_backend.domain.entities.export_plan import ExportAction, ExportPlanItem
from music_manager_backend.infrastructure.filesystem import ExportFileWriter
from music_manager_backend.shared.errors import ValidationError


def test_writer_creates_folders_and_replaces_managed_copies(tmp_path: Path) -> None:
    root = tmp_path / "usb"
    root.mkdir()
    source = root / "source.mp3"
    source.write_bytes(b"new audio")
    target = root / "_music_manager_export" / "Set" / "track.mp3"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old audio")
    environment = MusicEnvironment(id="env_1", name="USB", root_path=root)
    writer = ExportFileWriter()

    writer.create_folder(environment, target.parent)
    writer.copy_file(
        environment=environment,
        source_path=source,
        target_path=target,
        active_source_paths={source.resolve(strict=False)},
    )

    assert target.read_bytes() == b"new audio"
    assert source.read_bytes() == b"new audio"


def test_writer_treats_missing_stale_file_as_success(tmp_path: Path) -> None:
    root = tmp_path / "usb"
    root.mkdir()
    target = root / "_music_manager_export" / "Set" / "missing.mp3"

    ExportFileWriter().remove_stale_copy(
        MusicEnvironment(id="env_1", name="USB", root_path=root),
        target,
    )

    assert not target.exists()


def test_writer_rejects_target_outside_managed_root(tmp_path: Path) -> None:
    root = tmp_path / "usb"
    root.mkdir()
    environment = MusicEnvironment(id="env_1", name="USB", root_path=root)
    item = ExportPlanItem(
        action=ExportAction.COPY_FILE,
        source_path=root / "source.mp3",
        target_path=root / "outside.mp3",
    )

    with pytest.raises(ValidationError):
        ExportFileWriter().validate_plan_targets(environment=environment, items=(item,))


def test_writer_rejects_symlink_escape_from_managed_root(tmp_path: Path) -> None:
    root = tmp_path / "usb"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    managed = root / "_music_manager_export"
    managed.mkdir()
    escape = managed / "escape"
    try:
        escape.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available on this filesystem")

    environment = MusicEnvironment(id="env_1", name="USB", root_path=root)
    item = ExportPlanItem(
        action=ExportAction.COPY_FILE,
        source_path=root / "source.mp3",
        target_path=escape / "track.mp3",
    )

    with pytest.raises(ValidationError):
        ExportFileWriter().validate_plan_targets(environment=environment, items=(item,))
