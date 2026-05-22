from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from tinytag import TinyTag, TinyTagException

from music_manager_backend.domain.entities import AudioMetadata


class MetadataReader:
    def __init__(self, tag_factory: Callable[[str], Any] | None = None) -> None:
        self.tag_factory = tag_factory or TinyTag.get

    def read(self, path: Path) -> AudioMetadata:
        try:
            tag = self.tag_factory(str(path))
        except (TinyTagException, OSError, ValueError) as exc:
            return AudioMetadata(warnings=(f"metadata_unreadable: {exc}",))

        raw = _raw_metadata(tag)
        return AudioMetadata(
            title=_clean_text(_get_attr(tag, "title")),
            artist=_clean_text(_get_attr(tag, "artist")),
            album=_clean_text(_get_attr(tag, "album")),
            duration_seconds=_duration_seconds(_get_attr(tag, "duration")),
            bpm=_int_value(
                _first_present(_get_attr(tag, "bpm"), _get_attr(tag, "beats_per_minute"))
            ),
            key=_clean_text(_first_present(_get_attr(tag, "key"), _get_attr(tag, "initial_key"))),
            comment=_clean_text(
                _first_present(_get_attr(tag, "comment"), _get_attr(tag, "comments"))
            ),
            raw=raw,
        )


def _get_attr(tag: Any, name: str) -> object:
    return cast(object, getattr(tag, name, None))


def _first_present(*values: object) -> object:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _duration_seconds(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, str | int | float):
        return None
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    if duration <= 0:
        return None
    return int(round(duration))


def _int_value(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, str | int | float):
        return None
    try:
        parsed = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _raw_metadata(tag: Any) -> dict[str, object]:
    if hasattr(tag, "as_dict"):
        raw = cast(object, tag.as_dict())
        if isinstance(raw, dict):
            return _json_safe_dict(raw)

    values: dict[str, object] = {}
    for key, value in vars(tag).items():
        if key.startswith("_"):
            continue
        normalized = _json_safe_value(value)
        if normalized is not None:
            values[key] = normalized
    return values


def _json_safe_dict(values: dict[object, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key, value in values.items():
        normalized = _json_safe_value(value)
        if normalized is not None:
            safe[str(key)] = normalized
    return safe


def _json_safe_value(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple):
        return [item for item in (_json_safe_value(item) for item in value) if item is not None]
    return str(value)
