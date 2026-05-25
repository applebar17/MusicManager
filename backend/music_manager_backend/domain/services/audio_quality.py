PREVIEW_DURATION_SECONDS = 60
LIKELY_PREVIEW_WARNING = "likely_preview_download"


def is_likely_preview_duration(duration_seconds: int | None) -> bool:
    return duration_seconds is not None and duration_seconds < PREVIEW_DURATION_SECONDS


def audio_warnings(duration_seconds: int | None) -> list[str]:
    if is_likely_preview_duration(duration_seconds):
        return [LIKELY_PREVIEW_WARNING]
    return []
