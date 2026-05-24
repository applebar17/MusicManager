#!/usr/bin/env python3
"""Debug public SoundCloud playlist discovery and optional local import.

Examples:
  python3 scripts/debug_soundcloud_playlist.py "https://soundcloud.com/user/sets/list"
  python3 scripts/debug_soundcloud_playlist.py URL --save-html local/soundcloud.html
  python3 scripts/debug_soundcloud_playlist.py URL --environment-id env_123 --import-local
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import NoReturn

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from music_manager_backend.application.use_cases.import_soundcloud_playlist import (  # noqa: E402
    ImportSoundCloudPlaylist,
)
from music_manager_backend.infrastructure.persistence import (  # noqa: E402
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteRemotePlaylistRepository,
    SqliteSongRepository,
    SqliteSyncSnapshotRepository,
)
from music_manager_backend.infrastructure.persistence.migration_runner import (  # noqa: E402
    upgrade_database,
)
from music_manager_backend.infrastructure.persistence.sqlite import connect  # noqa: E402
from music_manager_backend.infrastructure.soundcloud.public_html_parser import (  # noqa: E402
    PublicPlaylistHtmlParser,
)
from music_manager_backend.infrastructure.soundcloud.public_playlist_importer import (  # noqa: E402
    DEFAULT_USER_AGENT,
    HttpSoundCloudApiClient,
    PublicPlaylistImporter,
)
from music_manager_backend.ports.soundcloud_models import ParsedSoundCloudPlaylist  # noqa: E402
from music_manager_backend.shared.errors import MusicManagerError  # noqa: E402
from music_manager_backend.shared.settings import get_settings  # noqa: E402


class StaticPlaylistImporter:
    def __init__(self, playlist: ParsedSoundCloudPlaylist) -> None:
        self.playlist = playlist

    def import_playlist(self, _url: str) -> ParsedSoundCloudPlaylist:
        return self.playlist


class StaticHtmlFetcher:
    def __init__(self, html: str) -> None:
        self.html = html

    def fetch(self, _url: str) -> str:
        return self.html


def main() -> int:
    args = _parse_args()
    try:
        response = _fetch(args.url, timeout_seconds=args.timeout)
    except httpx.HTTPError as exc:
        _fail(f"fetch failed: {exc!r}")

    html = response.text
    if args.save_html is not None:
        args.save_html.parent.mkdir(parents=True, exist_ok=True)
        args.save_html.write_text(html)

    parser = PublicPlaylistHtmlParser()
    html_playlist = parser.parse(html, source_url=args.url)
    playlist = PublicPlaylistImporter(
        fetcher=StaticHtmlFetcher(html),
        parser=parser,
        api_client=HttpSoundCloudApiClient(),
    ).import_playlist(args.url)
    diagnostics = _diagnose_html(
        response=response,
        html=html,
        html_playlist=html_playlist,
        playlist=playlist,
    )

    if args.json:
        payload: dict[str, object] = {
            "diagnostics": diagnostics,
            "playlist": {
                "source_url": playlist.source_url,
                "title": playlist.title,
                "track_count": len(playlist.tracks),
                "warnings": list(playlist.warnings),
                "tracks": [asdict(track) for track in playlist.tracks[: args.limit]],
            },
        }
        if args.import_local:
            payload["import_result"] = _import_local(args.environment_id, args.url, playlist)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    _print_diagnostics(diagnostics)
    _print_playlist(playlist, limit=args.limit)

    if args.import_local:
        result = _import_local(args.environment_id, args.url, playlist)
        print("\nLOCAL IMPORT")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and parse a public SoundCloud playlist URL with diagnostics.",
    )
    parser.add_argument("url", help="Public SoundCloud playlist URL")
    parser.add_argument("--environment-id", help="Existing local environment id for --import-local")
    parser.add_argument(
        "--import-local",
        action="store_true",
        help="Run the durable import use case after parsing. Requires --environment-id.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--limit", type=int, default=20, help="Maximum tracks to print")
    parser.add_argument("--save-html", type=Path, help="Write fetched HTML to this path")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    args = parser.parse_args()
    if args.import_local and not args.environment_id:
        parser.error("--import-local requires --environment-id")
    return args


def _fetch(url: str, *, timeout_seconds: float) -> httpx.Response:
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    with httpx.Client(follow_redirects=True, timeout=timeout_seconds, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response


def _diagnose_html(
    *,
    response: httpx.Response,
    html: str,
    html_playlist: ParsedSoundCloudPlaylist,
    playlist: ParsedSoundCloudPlaylist,
) -> dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")
    text_probe = html.casefold()
    return {
        "requested_url": str(response.request.url),
        "final_url": str(response.url),
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "html_bytes": len(response.content),
        "html_chars": len(html),
        "title": soup.title.get_text(strip=True) if soup.title else None,
        "og_title": _meta_content(soup, 'meta[property="og:title"]'),
        "track_row_count": len(soup.select("li.trackList__item")),
        "track_title_anchor_count": len(soup.select("a.trackItem__trackTitle")),
        "paging_eof_present": soup.select_one(".paging-eof") is not None,
        "script_count": len(soup.select("script")),
        "hydration_marker_present": "__sc_hydration" in text_probe,
        "soundcloud_track_api_hint_present": "soundcloud://tracks:" in text_probe,
        "soundcloud_playlist_api_hint_present": "soundcloud://playlists:" in text_probe,
        "sign_in_hint_present": "sign in" in text_probe or "log in" in text_probe,
        "captcha_hint_present": "captcha" in text_probe,
        "html_parser_track_count": len(html_playlist.tracks),
        "html_parser_warnings": list(html_playlist.warnings),
        "parsed_track_count": len(playlist.tracks),
        "parser_warnings": list(playlist.warnings),
    }


def _meta_content(soup: BeautifulSoup, selector: str) -> str | None:
    element = soup.select_one(selector)
    value = element.get("content") if element else None
    return value if isinstance(value, str) else None


def _print_diagnostics(diagnostics: dict[str, object]) -> None:
    print("FETCH / HTML DIAGNOSTICS")
    for key, value in diagnostics.items():
        print(f"- {key}: {value}")


def _print_playlist(playlist: ParsedSoundCloudPlaylist, *, limit: int) -> None:
    print("\nPARSED PLAYLIST")
    print(f"- source_url: {playlist.source_url}")
    print(f"- title: {playlist.title}")
    print(f"- tracks: {len(playlist.tracks)}")
    print(f"- warnings: {', '.join(playlist.warnings) if playlist.warnings else '(none)'}")
    for track in playlist.tracks[:limit]:
        print(
            f"  {track.position:03d}. {track.uploader or 'Unknown'} - {track.title} "
            f"[{track.canonical_track_url}]"
        )
    if len(playlist.tracks) > limit:
        print(f"  ... {len(playlist.tracks) - limit} more")


def _import_local(
    environment_id: str | None, url: str, playlist: ParsedSoundCloudPlaylist
) -> dict[str, object]:
    if environment_id is None:
        _fail("internal error: environment_id is required for local import")

    settings = get_settings()
    upgrade_database(settings.database_path)
    connection = connect(settings.database_path)
    try:
        result = ImportSoundCloudPlaylist(
            environments=SqliteEnvironmentRepository(connection),
            remote_playlists=SqliteRemotePlaylistRepository(connection),
            playlists=SqlitePlaylistRepository(connection),
            songs=SqliteSongRepository(connection),
            audio_files=SqliteAudioFileRepository(connection),
            match_links=SqliteMatchLinkRepository(connection),
            sync_snapshots=SqliteSyncSnapshotRepository(connection),
            importer=StaticPlaylistImporter(playlist),
        ).execute(environment_id, url)
    except MusicManagerError as exc:
        return {
            "ok": False,
            "code": exc.code,
            "message": exc.message,
        }

    return {
        "ok": True,
        "result": result.model_dump(),
    }


def _fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(main())
