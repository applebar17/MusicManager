from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MusicEnvironment:
    id: str
    name: str
    root_path: Path
    deprecated_folder_name: str = "_deprecated"
    default_export_profile: str = "generic_usb_folder_mirror"
    archived_at: str | None = None
