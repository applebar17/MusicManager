import re


def normalize_title(value: str) -> str:
    cleaned = value.casefold()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return cleaned.strip()

