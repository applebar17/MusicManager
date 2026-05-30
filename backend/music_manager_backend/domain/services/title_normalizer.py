import re

_PROMO_DOWNLOAD_PATTERN = re.compile(
    r"\b(?:free[\s._\-/]*(?:download|dl)|download|dl)\b",
    re.IGNORECASE,
)
_VERSION_DESCRIPTOR_PATTERN = re.compile(
    r"\b(?:(?:club|radio|single|extended|original|vocal|instrumental|dub|short|long|"
    r"festival|main|album)[\s._\-/]+(?:edit|mix|remix|version)|"
    r"(?:edit|remix|mix|version|rework|refix|bootleg|dub|vip|remaster(?:ed)?))\b",
    re.IGNORECASE,
)


def normalize_title(value: str) -> str:
    cleaned = value.casefold()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return cleaned.strip()


def normalize_match_title(value: str) -> str:
    return normalize_title(_PROMO_DOWNLOAD_PATTERN.sub(" ", value))


def normalize_versionless_match_title(value: str) -> str:
    without_promo = _PROMO_DOWNLOAD_PATTERN.sub(" ", value)
    return normalize_title(_VERSION_DESCRIPTOR_PATTERN.sub(" ", without_promo))

