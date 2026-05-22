import re
from pathlib import Path

RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def sanitize_path_part(value: str, *, fallback: str = "Untitled") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in RESERVED_NAMES:
        cleaned = f"{cleaned}_"
    return cleaned[:120]


def unique_path(path: Path, used_paths: set[Path]) -> Path:
    if path not in used_paths:
        used_paths.add(path)
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem} ({index}){suffix}"
        if candidate not in used_paths:
            used_paths.add(candidate)
            return candidate
        index += 1
