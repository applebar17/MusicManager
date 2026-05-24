import json
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
        tracks: list[ParsedSoundCloudTrack] = []

        if title is None:
            warnings.append("soundcloud_public_html_missing_playlist_title")

        if rows and soup.select_one(".paging-eof") is None:
            warnings.append("soundcloud_public_html_missing_eof_marker")

        if rows:
            for index, row in enumerate(rows, start=1):
                track = _parse_track_row(row, index=index, warnings=warnings)
                if track is not None:
                    tracks.append(track)
        else:
            tracks = _extract_hydrated_tracks(html, source_url=source_url, warnings=warnings)
            if not tracks:
                tracks = _extract_schema_tracks(soup, source_url=source_url, warnings=warnings)
            if not tracks:
                warnings.append("soundcloud_public_html_no_track_rows")

        return ParsedSoundCloudPlaylist(
            source_url=source_url,
            title=title,
            tracks=tuple(tracks),
            warnings=tuple(warnings),
        )


def parse_soundcloud_api_playlist(
    data: dict[str, object],
    *,
    source_url: str,
    fallback_title: str | None = None,
    warnings: tuple[str, ...] = (),
) -> ParsedSoundCloudPlaylist:
    parsed_warnings = list(warnings)
    title = _string(data.get("title")) or fallback_title
    raw_tracks = data.get("tracks")
    tracks: list[ParsedSoundCloudTrack] = []

    if not isinstance(raw_tracks, list):
        parsed_warnings.append("soundcloud_api_playlist_missing_tracks")
        raw_tracks = []

    for index, raw_track in enumerate(raw_tracks, start=1):
        if not isinstance(raw_track, dict):
            parsed_warnings.append(f"soundcloud_api_track_{index}_invalid")
            continue
        track = _parse_hydrated_track(
            raw_track,
            index=index,
            source_url=source_url,
            warnings=parsed_warnings,
            warning_prefix="soundcloud_api_track",
        )
        if track is not None:
            tracks.append(track)

    track_count = data.get("track_count")
    if isinstance(track_count, int) and track_count > len(tracks):
        parsed_warnings.append("soundcloud_api_incomplete_track_data")

    return ParsedSoundCloudPlaylist(
        source_url=source_url,
        title=title,
        tracks=tuple(tracks),
        warnings=tuple(parsed_warnings),
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


def _extract_hydrated_tracks(
    html: str, *, source_url: str, warnings: list[str]
) -> list[ParsedSoundCloudTrack]:
    match = re.search(r"window\.__sc_hydration\s*=\s*(\[.*?\]);\s*</script>", html, re.DOTALL)
    if match is None:
        return []

    try:
        hydration = json.loads(match.group(1))
    except json.JSONDecodeError:
        warnings.append("soundcloud_hydration_json_decode_failed")
        return []

    playlist_data = None
    for item in hydration:
        if isinstance(item, dict) and item.get("hydratable") == "playlist":
            data = item.get("data")
            if isinstance(data, dict):
                playlist_data = data
                break

    if playlist_data is None:
        return []

    raw_tracks = playlist_data.get("tracks")
    if not isinstance(raw_tracks, list):
        return []

    tracks: list[ParsedSoundCloudTrack] = []
    for index, raw_track in enumerate(raw_tracks, start=1):
        if not isinstance(raw_track, dict):
            warnings.append(f"soundcloud_hydration_track_{index}_invalid")
            continue
        track = _parse_hydrated_track(
            raw_track,
            index=index,
            source_url=source_url,
            warnings=warnings,
        )
        if track is not None:
            tracks.append(track)

    track_count = playlist_data.get("track_count")
    if isinstance(track_count, int) and track_count > len(tracks):
        warnings.append("soundcloud_hydration_incomplete_track_data")

    return tracks


def _parse_hydrated_track(
    raw_track: dict[str, object],
    *,
    index: int,
    source_url: str,
    warnings: list[str],
    warning_prefix: str = "soundcloud_hydration_track",
) -> ParsedSoundCloudTrack | None:
    title = _string(raw_track.get("title"))
    canonical_track_url = _string(raw_track.get("permalink_url"))
    if title is None or canonical_track_url is None:
        warnings.append(f"{warning_prefix}_{index}_missing_title_or_url")
        return None

    user = raw_track.get("user")
    user_data = user if isinstance(user, dict) else {}
    publisher_metadata = raw_track.get("publisher_metadata")
    publisher_data = publisher_metadata if isinstance(publisher_metadata, dict) else {}
    uploader = _string(publisher_data.get("artist")) or _string(user_data.get("username"))
    uploader_url = _string(user_data.get("permalink_url"))
    playlist_track_url = _playlist_scoped_track_url(canonical_track_url, source_url=source_url)
    duration_ms = _int(raw_track.get("full_duration")) or _int(raw_track.get("duration"))

    return ParsedSoundCloudTrack(
        position=index,
        title=title,
        uploader=uploader,
        uploader_url=uploader_url,
        canonical_track_url=_strip_query_and_fragment(canonical_track_url),
        playlist_track_url=playlist_track_url,
        artwork_url=_string(raw_track.get("artwork_url")),
        play_count=_int(raw_track.get("playback_count")),
        duration_seconds=round(duration_ms / 1000) if duration_ms is not None else None,
        raw={
            key: value
            for key, value in {
                "track_id": _string(raw_track.get("id")),
                "track_urn": _string(raw_track.get("urn")),
                "track_permalink_url": canonical_track_url,
            }.items()
            if value
        },
    )


def _extract_schema_tracks(
    soup: BeautifulSoup, *, source_url: str, warnings: list[str]
) -> list[ParsedSoundCloudTrack]:
    rows = soup.select('section.tracklist article[itemprop="track"]')
    tracks: list[ParsedSoundCloudTrack] = []
    for index, row in enumerate(rows, start=1):
        title_anchor = row.select_one('h2[itemprop="name"] a[itemprop="url"]')
        if not isinstance(title_anchor, Tag):
            warnings.append(f"soundcloud_schema_track_{index}_missing_track_title")
            continue
        title = title_anchor.get_text(strip=True)
        raw_track_href = _attribute(title_anchor, "href")
        if not title or raw_track_href is None:
            warnings.append(f"soundcloud_schema_track_{index}_missing_track_title_or_url")
            continue
        canonical_track_url = _normalize_soundcloud_url(raw_track_href)
        uploader_anchor = row.select_one('h2[itemprop="name"] a:not([itemprop="url"])')
        uploader = uploader_anchor.get_text(strip=True) if uploader_anchor else None
        uploader_href = _attribute(uploader_anchor, "href") if uploader_anchor else None
        duration = _attribute(row.select_one('meta[itemprop="duration"]'), "content")

        tracks.append(
            ParsedSoundCloudTrack(
                position=index,
                title=title,
                uploader=uploader or None,
                uploader_url=_normalize_soundcloud_url(uploader_href) if uploader_href else None,
                canonical_track_url=_strip_query_and_fragment(canonical_track_url),
                playlist_track_url=_playlist_scoped_track_url(
                    canonical_track_url, source_url=source_url
                ),
                duration_seconds=_parse_iso_duration_seconds(duration),
                raw={"track_href": raw_track_href},
            )
        )

    if tracks:
        warnings.append("soundcloud_schema_tracklist_used")
    return tracks


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


def _playlist_scoped_track_url(canonical_track_url: str, *, source_url: str) -> str:
    source_path = urlsplit(source_url).path.strip("/")
    if not source_path:
        return _strip_query_and_fragment(canonical_track_url)
    return f"{_strip_query_and_fragment(canonical_track_url)}?in={source_path}"


def _parse_iso_duration_seconds(value: str | None) -> int | None:
    if not value:
        return None
    match = re.fullmatch(
        r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
        value,
    )
    if match is None:
        return None
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return hours * 3600 + minutes * 60 + seconds


def _string(value: object) -> str | None:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _attribute(element: Tag | None, name: str) -> str | None:
    if element is None:
        return None

    value = element.get(name)
    return value if isinstance(value, str) and value.strip() else None
