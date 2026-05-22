from datetime import UTC

from music_manager_backend.shared.time import utc_now, utc_now_iso


def test_utc_now_is_timezone_aware() -> None:
    value = utc_now()

    assert value.tzinfo is UTC


def test_utc_now_iso_includes_utc_offset() -> None:
    assert utc_now_iso().endswith("+00:00")
