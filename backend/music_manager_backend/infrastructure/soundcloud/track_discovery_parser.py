import re
import shlex
from html import unescape
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from music_manager_backend.ports.soundcloud_discovery import (
    SoundCloudDiscoveryLink,
    SoundCloudTrackDiscovery,
)

SOUNDCLOUD_BASE_URL = "https://soundcloud.com"
BUY_DOWNLOAD_HOST_HINTS = (
    "bandcamp.",
    "beatport.",
    "juno.",
    "hypeddit.",
    "toneden.",
    "dropbox.",
    "drive.google.",
    "mega.",
    "mediafire.",
    "we.tl",
    "wetransfer.",
)


class SoundCloudTrackDiscoveryHtmlParser:
    def parse(self, html: str, *, source_url: str) -> SoundCloudTrackDiscovery:
        soup = BeautifulSoup(html, "html.parser")
        track_urn = _extract_track_urn(html)
        description = _description_text(soup)
        purchase_link = _purchase_button_link(soup)
        links = _links(soup)
        tags = _tags(soup)
        release_metadata = _release_metadata(soup)
        warnings = _warnings(
            description=description,
            links=links,
            purchase_link=purchase_link,
        )

        return SoundCloudTrackDiscovery(
            track_url=source_url,
            track_urn=track_urn,
            title=_meta_content(soup, "og:title"),
            artist=_artist_name(soup),
            description=description,
            purchase_title=purchase_link.label if purchase_link is not None else None,
            purchase_url=purchase_link.url if purchase_link is not None else None,
            links=tuple(_dedupe_links((*links, *((purchase_link,) if purchase_link else ())))),
            tags=tuple(tags),
            release_metadata=release_metadata,
            warnings=tuple(warnings),
            raw={"track_urn": track_urn} if track_urn is not None else {},
        )


def merge_soundcloud_api_track_discovery(
    discovery: SoundCloudTrackDiscovery,
    api_track: dict[str, object],
) -> SoundCloudTrackDiscovery:
    title = _api_text(api_track.get("title")) or discovery.title
    artist = _api_user_name(api_track) or discovery.artist
    description = _api_text(api_track.get("description")) or discovery.description
    track_url = _api_url(api_track.get("permalink_url")) or discovery.track_url
    track_urn = _api_track_urn(api_track) or discovery.track_urn
    purchase_title = _api_text(api_track.get("purchase_title")) or discovery.purchase_title
    purchase_url = _api_url(api_track.get("purchase_url")) or discovery.purchase_url
    downloadable = _api_bool(api_track.get("downloadable"), fallback=discovery.downloadable)
    download_url = _api_url(api_track.get("download_url")) or discovery.download_url

    links = list(discovery.links)
    if purchase_url is not None:
        links.append(
            SoundCloudDiscoveryLink(
                url=purchase_url,
                label=purchase_title or "Buy",
                kind=_link_kind(purchase_url, context=purchase_title or "Buy"),
                source="api_purchase_url",
            )
        )
    if download_url is not None:
        links.append(
            SoundCloudDiscoveryLink(
                url=download_url,
                label="Download",
                kind="download",
                source="api_download_url",
            )
        )

    deduped_links = tuple(_dedupe_links(links))
    tags = tuple(_dedupe_text((*discovery.tags, *_api_tags(api_track))))
    warnings = tuple(
        _warnings(
            description=description,
            links=deduped_links,
            purchase_link=next(
                (link for link in deduped_links if link.url == purchase_url),
                None,
            ),
        )
    )

    return SoundCloudTrackDiscovery(
        track_url=track_url,
        track_urn=track_urn,
        title=title,
        artist=artist,
        description=description,
        purchase_title=purchase_title,
        purchase_url=purchase_url,
        downloadable=downloadable,
        download_url=download_url,
        links=deduped_links,
        tags=tags,
        release_metadata=discovery.release_metadata,
        warnings=warnings,
        raw={**discovery.raw, "api_track": api_track},
    )


def _extract_track_urn(html: str) -> str | None:
    unescaped = unescape(unquote(html))
    match = re.search(r"soundcloud:tracks:(\d+)", unescaped)
    return f"soundcloud:tracks:{match.group(1)}" if match else None


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    tag = soup.find("meta", attrs={"property": property_name})
    if tag is None:
        return None
    content = tag.get("content")
    return _clean_text(str(content)) if content else None


def _artist_name(soup: BeautifulSoup) -> str | None:
    candidate = soup.select_one(".userBadge__usernameLink .sc-truncate")
    if candidate is None:
        candidate = soup.select_one(".userBadge__usernameLink")
    return _clean_text(candidate.get_text(" ", strip=True)) if candidate else None


def _description_text(soup: BeautifulSoup) -> str | None:
    content = soup.select_one(".truncatedAudioInfo__content .sc-type-small.sc-text-body")
    if content is None:
        content = soup.select_one(".truncatedAudioInfo__content")
    if content is None:
        return None
    text = _clean_text(content.get_text("\n", strip=True))
    return text or None


def _purchase_button_link(soup: BeautifulSoup) -> SoundCloudDiscoveryLink | None:
    anchor = soup.select_one(".purchaseLink__container a[href]")
    if anchor is None:
        return None
    url = _decode_soundcloud_gate_url(str(anchor.get("href", "")))
    if not url:
        return None
    label = (
        _clean_text(str(anchor.get("aria-label") or anchor.get_text(" ", strip=True)))
        or "Buy"
    )
    return SoundCloudDiscoveryLink(
        url=url,
        label=label,
        kind=_link_kind(url, context=label),
        source="purchase_button",
    )


def _links(soup: BeautifulSoup) -> tuple[SoundCloudDiscoveryLink, ...]:
    description = soup.select_one(".truncatedAudioInfo__content")
    if description is None:
        return ()

    links: list[SoundCloudDiscoveryLink] = []
    for anchor in description.select("a[href]"):
        raw_href = str(anchor.get("href", ""))
        url = _normalize_url(_decode_soundcloud_gate_url(raw_href))
        if not url:
            continue
        label = _clean_text(
            str(anchor.get("title") or anchor.get_text(" ", strip=True) or url)
        )
        paragraph = anchor.find_parent("p")
        context = (
            _clean_text(paragraph.get_text(" ", strip=True))
            if paragraph is not None
            else label
        )
        links.append(
            SoundCloudDiscoveryLink(
                url=url,
                label=label,
                kind=_link_kind(url, context=context),
                source="description",
            )
        )
    return tuple(_dedupe_links(links))


def _tags(soup: BeautifulSoup) -> list[str]:
    return [
        text
        for text in (
            _clean_text(tag.get_text(" ", strip=True))
            for tag in soup.select(".soundTags .sc-tagContent")
        )
        if text
    ]


def _release_metadata(soup: BeautifulSoup) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for term in soup.select(".listenInfo__releaseList dt"):
        value = term.find_next_sibling("dd")
        if value is None:
            continue
        key = _clean_text(term.get_text(" ", strip=True)).rstrip(":")
        data = _clean_text(value.get_text(" ", strip=True))
        if key and data:
            metadata[key] = data
    return metadata


def _warnings(
    *,
    description: str | None,
    links: tuple[SoundCloudDiscoveryLink, ...],
    purchase_link: SoundCloudDiscoveryLink | None,
) -> list[str]:
    warnings: list[str] = []
    lower_description = (description or "").lower()
    has_download_or_purchase_link = purchase_link is not None or any(
        link.kind in {"buy", "download", "buy_or_download"} for link in links
    )
    if "free download" in lower_description and not has_download_or_purchase_link:
        warnings.append("free_download_mentioned_without_link")
    if (
        "low quality" in lower_description
        or "promotional purposes" in lower_description
        or "promo purposes" in lower_description
    ):
        warnings.append("promotional_low_quality_notice")
    if not has_download_or_purchase_link:
        warnings.append("no_purchase_or_download_link_found")
    return warnings


def _decode_soundcloud_gate_url(url: str) -> str:
    if url.startswith("/"):
        url = f"{SOUNDCLOUD_BASE_URL}{url}"
    parsed = urlparse(url)
    if parsed.netloc == "gate.sc":
        values = parse_qs(parsed.query).get("url")
        return values[0] if values else url
    return url


def _normalize_url(url: str) -> str:
    if url.startswith("mailto:"):
        return url
    if url.startswith("@"):
        return f"{SOUNDCLOUD_BASE_URL}/{url[1:]}"
    if url.startswith("/"):
        return f"{SOUNDCLOUD_BASE_URL}{url}"
    return url


def _api_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = _clean_text(value)
    return text or None


def _api_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    url = _normalize_url(_decode_soundcloud_gate_url(value))
    return url or None


def _api_bool(value: object, *, fallback: bool | None) -> bool | None:
    if isinstance(value, bool):
        return value
    return fallback


def _api_track_urn(api_track: dict[str, object]) -> str | None:
    urn = _api_text(api_track.get("urn"))
    if urn is not None:
        return urn
    track_id = api_track.get("id")
    if isinstance(track_id, (int, str)) and str(track_id).strip():
        return f"soundcloud:tracks:{track_id}"
    return None


def _api_user_name(api_track: dict[str, object]) -> str | None:
    user = api_track.get("user")
    if not isinstance(user, dict):
        return None
    return _api_text(user.get("username"))


def _api_tags(api_track: dict[str, object]) -> tuple[str, ...]:
    tags: list[str] = []
    genre = _api_text(api_track.get("genre"))
    if genre is not None:
        tags.append(genre)

    raw_tag_list = _api_text(api_track.get("tag_list"))
    if raw_tag_list is None:
        return tuple(tags)
    try:
        tags.extend(shlex.split(raw_tag_list))
    except ValueError:
        tags.extend(raw_tag_list.split())
    return tuple(tags)


def _link_kind(url: str, *, context: str | None = None) -> str:
    lower_url = url.lower()
    lower_context = (context or "").lower()
    if lower_url.startswith("mailto:"):
        return "contact"
    if any(hint in lower_url for hint in BUY_DOWNLOAD_HOST_HINTS):
        if "download" in lower_context or "free" in lower_context:
            return "download"
        return "buy_or_download"
    if any(word in lower_context for word in ("buy", "purchase", "support the label")):
        return "buy"
    if "download" in lower_context:
        return "download"
    if "instagram." in lower_url or "facebook." in lower_url:
        return "artist_social"
    if "soundcloud.com" in lower_url:
        return "soundcloud_profile"
    return "external"


def _dedupe_links(
    links: tuple[SoundCloudDiscoveryLink, ...] | list[SoundCloudDiscoveryLink],
) -> list[SoundCloudDiscoveryLink]:
    deduped: list[SoundCloudDiscoveryLink] = []
    seen: set[str] = set()
    for link in links:
        if link.url in seen:
            continue
        seen.add(link.url)
        deduped.append(link)
    return deduped


def _dedupe_text(values: tuple[str, ...]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
