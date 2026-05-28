import re
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


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
