import json
from dataclasses import dataclass
from pathlib import Path

from music_manager_backend.domain.services.export_layout import (
    EXPORT_MANIFEST_NAME,
    EXPORT_METADATA_FOLDER_NAME,
)


@dataclass(frozen=True)
class ExportManifest:
    targets: frozenset[Path]


def read_export_manifest(root_path: Path) -> ExportManifest:
    path = _manifest_path(root_path)
    if not path.exists():
        return ExportManifest(targets=frozenset())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ExportManifest(targets=frozenset())

    raw_targets = payload.get("targets", []) if isinstance(payload, dict) else []
    if not isinstance(raw_targets, list):
        return ExportManifest(targets=frozenset())
    return ExportManifest(
        targets=frozenset(
            Path(item).resolve(strict=False)
            for item in raw_targets
            if isinstance(item, str) and item
        )
    )


def update_export_manifest(
    *,
    root_path: Path,
    add_targets: set[Path],
    remove_targets: set[Path],
) -> None:
    if not add_targets and not remove_targets:
        return
    current = set(read_export_manifest(root_path).targets)
    current.difference_update(path.resolve(strict=False) for path in remove_targets)
    current.update(path.resolve(strict=False) for path in add_targets)

    path = _manifest_path(root_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "targets": [str(item) for item in sorted(current)],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _manifest_path(root_path: Path) -> Path:
    return root_path / EXPORT_METADATA_FOLDER_NAME / EXPORT_MANIFEST_NAME
