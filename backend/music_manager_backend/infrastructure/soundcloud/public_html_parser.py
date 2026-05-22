import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from music_manager_backend.ports.soundcloud_models import (
    ParsedSoundCloudPlaylist,
    ParsedSoundCloudTrack,
)

SOUNDCLOUD_BASE_URL = "https://soundcloud.com"


class PublicPlaylistHtmlParser:
    def parse(self, html: str, *, source_url: str) -> ParsedSoundCloudPlaylist:
        soup = BeautifulSoup(html, "html.parser")
        warnings: list[str] = []
        rows = soup.select("li.trackList__item")
        title = _extract_playlist_title(soup)

        if title is None:
            warnings.append("soundcloud_public_html_missing_playlist_title")

        if not rows:
            warnings.append("soundcloud_public_html_no_track_rows")

        if rows and soup.select_one(".paging-eof") is None:
            warnings.append("soundcloud_public_html_missing_eof_marker")

        tracks: list[ParsedSoundCloudTrack] = []
        for index, row in enumerate(rows, start=1):
            track = _parse_track_row(row, index=index, warnings=warnings)
            if track is not None:
                tracks.append(track)

        return ParsedSoundCloudPlaylist(
            source_url=source_url,
            title=title,
            tracks=tuple(tracks),
            warnings=tuple(warnings),
        )


def _parse_track_row(
    row: Tag, *, index: int, warnings: list[str]
) -> ParsedSoundCloudTrack | None:
    title_anchor = row.select_one("a.trackItem__trackTitle")
    if not isinstance(title_anchor, Tag):
        warnings.append(f"soundcloud_track_row_{index}_missing_track_title")
        return None

    title = title_anchor.get_text(strip=True)
    if not title:
        warnings.append(f"soundcloud_track_row_{index}_missing_track_title")
        return None

    raw_track_href = _attribute(title_anchor, "href")
    if raw_track_href is None:
        warnings.append(f"soundcloud_track_row_{index}_missing_track_href")
        return None

    playlist_track_url = _normalize_soundcloud_url(raw_track_href)
    canonical_track_url = _strip_query_and_fragment(playlist_track_url)
    uploader_anchor = row.select_one("a.trackItem__username")
    uploader = None
    raw_uploader_href = None
    if isinstance(uploader_anchor, Tag):
        uploader = uploader_anchor.get_text(strip=True)
        raw_uploader_href = _attribute(uploader_anchor, "href")
    uploader_url = _normalize_soundcloud_url(raw_uploader_href) if raw_uploader_href else None
    artwork_style = _attribute(row.select_one("span.sc-artwork"), "style")

    return ParsedSoundCloudTrack(
        position=_extract_position(row, fallback=index),
        title=title,
        uploader=uploader or None,
        uploader_url=uploader_url,
        canonical_track_url=canonical_track_url,
        playlist_track_url=playlist_track_url,
        artwork_url=_extract_artwork_url(artwork_style),
        play_count=_extract_play_count(row),
        duration_seconds=None,
        raw={
            key: value
            for key, value in {
                "track_href": raw_track_href,
                "uploader_href": raw_uploader_href,
                "artwork_style": artwork_style,
            }.items()
            if value
        },
    )


def _extract_playlist_title(soup: BeautifulSoup) -> str | None:
    title_selectors = (
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
    )
    for selector in title_selectors:
        element = soup.select_one(selector)
        value = _attribute(element, "content")
        if value:
            return _clean_playlist_title(value)

    title = soup.title.get_text(strip=True) if soup.title is not None else None
    return _clean_playlist_title(title) if title else None


def _clean_playlist_title(value: str) -> str:
    return re.sub(r"\s+\|\s+SoundCloud$", "", value.strip())


def _extract_position(row: Tag, *, fallback: int) -> int:
    number = row.select_one(".trackItem__number .trackItem__separator")
    text = number.get_text(" ", strip=True) if number is not None else ""
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else fallback


def _extract_artwork_url(style: str | None) -> str | None:
    if not style:
        return None

    match = re.search(r"url\((?:&quot;|['\"]?)(.*?)(?:&quot;|['\"]?)\)", style)
    return match.group(1) if match else None


def _extract_play_count(row: Tag) -> int | None:
    element = row.select_one(".trackItem__playCount")
    if element is None:
        return None

    text = element.get_text(" ", strip=True)
    match = re.search(r"(\d+(?:[,.]\d+)?)([KkMm])?", text)
    if match is None:
        return None

    value = float(match.group(1).replace(",", ""))
    suffix = match.group(2)
    if suffix is not None:
        multiplier = 1_000 if suffix.casefold() == "k" else 1_000_000
        value *= multiplier
    return int(value)


def _normalize_soundcloud_url(value: str) -> str:
    return urljoin(f"{SOUNDCLOUD_BASE_URL}/", value)


def _strip_query_and_fragment(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _attribute(element: Tag | None, name: str) -> str | None:
    if element is None:
        return None

    value = element.get(name)
    return value if isinstance(value, str) and value.strip() else None
