import re
from time import sleep
from typing import Protocol

import httpx

from music_manager_backend.infrastructure.soundcloud.public_html_parser import (
    PublicPlaylistHtmlParser,
    parse_soundcloud_api_playlist,
)
from music_manager_backend.ports.soundcloud import SoundCloudHtmlFetcher
from music_manager_backend.ports.soundcloud_models import ParsedSoundCloudPlaylist
from music_manager_backend.shared.errors import InfrastructureError

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; MusicManager/0.1; "
    "+https://github.com/local/music-manager)"
)
TRACK_LOOKUP_CHUNK_SIZE = 50
SOUNDCLOUD_REQUEST_ATTEMPTS = 3
SOUNDCLOUD_RETRY_BACKOFF_SECONDS = 0.25
TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


class SoundCloudPublicApiClient(Protocol):
    def fetch_text(self, url: str) -> str:
        pass

    def fetch_json(self, url: str, *, params: dict[str, str]) -> dict[str, object] | list[object]:
        pass


class HttpSoundCloudHtmlFetcher:
    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        attempts: int = SOUNDCLOUD_REQUEST_ATTEMPTS,
        retry_backoff_seconds: float = SOUNDCLOUD_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.attempts = attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    def fetch(self, url: str) -> str:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout_seconds,
                headers={"User-Agent": DEFAULT_USER_AGENT},
            ) as client:
                response = _get_with_retries(
                    client,
                    url,
                    attempts=self.attempts,
                    retry_backoff_seconds=self.retry_backoff_seconds,
                )
        except httpx.HTTPError as exc:
            raise InfrastructureError(
                f"Could not fetch SoundCloud public playlist: {url}",
                code="soundcloud_public_fetch_failed",
            ) from exc

        return response.text


class HttpSoundCloudApiClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        attempts: int = SOUNDCLOUD_REQUEST_ATTEMPTS,
        retry_backoff_seconds: float = SOUNDCLOUD_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.attempts = attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    def fetch_text(self, url: str) -> str:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout_seconds,
                headers={"User-Agent": DEFAULT_USER_AGENT},
            ) as client:
                response = _get_with_retries(
                    client,
                    url,
                    attempts=self.attempts,
                    retry_backoff_seconds=self.retry_backoff_seconds,
                )
        except httpx.HTTPError as exc:
            raise InfrastructureError(
                f"Could not fetch SoundCloud public asset: {url}",
                code="soundcloud_public_asset_fetch_failed",
            ) from exc

        return response.text

    def fetch_json(self, url: str, *, params: dict[str, str]) -> dict[str, object] | list[object]:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout_seconds,
                headers={
                    "Accept": "application/json",
                    "User-Agent": DEFAULT_USER_AGENT,
                },
            ) as client:
                response = _get_with_retries(
                    client,
                    url,
                    params=params,
                    attempts=self.attempts,
                    retry_backoff_seconds=self.retry_backoff_seconds,
                )
        except httpx.HTTPError as exc:
            raise InfrastructureError(
                f"Could not fetch SoundCloud public API data: {url}",
                code="soundcloud_public_api_fetch_failed",
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise InfrastructureError(
                f"SoundCloud public API returned invalid JSON: {url}",
                code="soundcloud_public_api_invalid_json",
            ) from exc

        if not isinstance(payload, (dict, list)):
            raise InfrastructureError(
                f"SoundCloud public API returned unexpected payload: {url}",
                code="soundcloud_public_api_unexpected_payload",
            )
        return payload


class PublicPlaylistImporter:
    def __init__(
        self,
        *,
        fetcher: SoundCloudHtmlFetcher | None = None,
        parser: PublicPlaylistHtmlParser | None = None,
        api_client: SoundCloudPublicApiClient | None = None,
    ) -> None:
        self.fetcher = fetcher or HttpSoundCloudHtmlFetcher()
        self.parser = parser or PublicPlaylistHtmlParser()
        self.api_client = api_client if api_client is not None else (
            HttpSoundCloudApiClient() if fetcher is None else None
        )

    def import_playlist(self, url: str) -> ParsedSoundCloudPlaylist:
        html = self.fetcher.fetch(url)
        playlist = self.parser.parse(html, source_url=url)
        return self._enrich_incomplete_playlist(html=html, source_url=url, playlist=playlist)

    def _enrich_incomplete_playlist(
        self, *, html: str, source_url: str, playlist: ParsedSoundCloudPlaylist
    ) -> ParsedSoundCloudPlaylist:
        if self.api_client is None:
            return playlist
        if "soundcloud_hydration_incomplete_track_data" not in playlist.warnings:
            return playlist

        try:
            playlist_id = _extract_playlist_id(html)
            client_id = _extract_client_id(html, api_client=self.api_client)
            if playlist_id is None or client_id is None:
                return _append_warning(playlist, "soundcloud_api_enrichment_unavailable")
            api_playlist = self.api_client.fetch_json(
                f"https://api-v2.soundcloud.com/playlists/{playlist_id}",
                params={"client_id": client_id, "representation": "full"},
            )
            if not isinstance(api_playlist, dict):
                return _append_warning(playlist, "soundcloud_api_playlist_unexpected_payload")
            api_playlist = _hydrate_blackbox_tracks(
                api_playlist,
                client_id=client_id,
                api_client=self.api_client,
            )
            enriched = parse_soundcloud_api_playlist(
                api_playlist,
                source_url=source_url,
                fallback_title=playlist.title,
                warnings=("soundcloud_api_enrichment_used",),
            )
        except InfrastructureError:
            return _append_warning(playlist, "soundcloud_api_enrichment_failed")

        if len(enriched.tracks) <= len(playlist.tracks):
            return _append_warning(playlist, "soundcloud_api_enrichment_did_not_add_tracks")
        return enriched


def _extract_playlist_id(html: str) -> str | None:
    match = re.search(r"soundcloud://playlists:(\d+)", html)
    return match.group(1) if match else None


def _extract_client_id(html: str, *, api_client: SoundCloudPublicApiClient) -> str | None:
    for asset_url in _extract_asset_urls(html):
        try:
            asset_text = api_client.fetch_text(asset_url)
        except InfrastructureError:
            continue
        match = re.search(r'client_id:"([A-Za-z0-9_-]{16,})"', asset_text)
        if match is not None:
            return match.group(1)
    return None


def _extract_asset_urls(html: str) -> list[str]:
    return list(
        dict.fromkeys(
            re.findall(r'https://a-v2\.sndcdn\.com/assets/[^"\s]+\.js', html)
        )
    )


def _hydrate_blackbox_tracks(
    api_playlist: dict[str, object],
    *,
    client_id: str,
    api_client: SoundCloudPublicApiClient,
) -> dict[str, object]:
    raw_tracks = api_playlist.get("tracks")
    if not isinstance(raw_tracks, list):
        return api_playlist

    missing_ids = [
        str(raw_track.get("id"))
        for raw_track in raw_tracks
        if isinstance(raw_track, dict)
        and raw_track.get("id") is not None
        and not raw_track.get("permalink_url")
    ]
    if not missing_ids:
        return api_playlist

    api_tracks: list[object] = []
    for chunk in _chunks(missing_ids, TRACK_LOOKUP_CHUNK_SIZE):
        chunk_tracks = api_client.fetch_json(
            "https://api-v2.soundcloud.com/tracks",
            params={"client_id": client_id, "ids": ",".join(chunk)},
        )
        if not isinstance(chunk_tracks, list):
            continue
        api_tracks.extend(chunk_tracks)

    tracks_by_id = {
        str(api_track.get("id")): api_track
        for api_track in api_tracks
        if isinstance(api_track, dict) and api_track.get("id") is not None
    }
    hydrated_tracks = [
        tracks_by_id.get(str(raw_track.get("id")), raw_track)
        if isinstance(raw_track, dict)
        else raw_track
        for raw_track in raw_tracks
    ]

    return {**api_playlist, "tracks": hydrated_tracks}


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _get_with_retries(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str] | None = None,
    attempts: int,
    retry_backoff_seconds: float,
) -> httpx.Response:
    last_response: httpx.Response | None = None
    for attempt in range(max(1, attempts)):
        try:
            response = client.get(url, params=params)
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt < attempts - 1:
                _sleep_before_retry(retry_backoff_seconds, attempt)
                continue
            raise

        last_response = response
        if response.status_code in TRANSIENT_STATUS_CODES and attempt < attempts - 1:
            _sleep_before_retry(retry_backoff_seconds, attempt)
            continue
        response.raise_for_status()
        return response

    if last_response is not None:
        last_response.raise_for_status()
    raise httpx.TransportError(f"SoundCloud request failed: {url}")


def _sleep_before_retry(retry_backoff_seconds: float, attempt: int) -> None:
    if retry_backoff_seconds <= 0:
        return
    sleep(retry_backoff_seconds * (attempt + 1))


def _append_warning(
    playlist: ParsedSoundCloudPlaylist, warning: str
) -> ParsedSoundCloudPlaylist:
    return ParsedSoundCloudPlaylist(
        source_url=playlist.source_url,
        title=playlist.title,
        tracks=playlist.tracks,
        warnings=(*playlist.warnings, warning),
    )
