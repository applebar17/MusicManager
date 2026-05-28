import json
import sqlite3
from typing import cast

from music_manager_backend.domain.entities import SoundCloudSourceDiscovery
from music_manager_backend.ports.soundcloud_discovery import SoundCloudDiscoveryLink


class SqliteSourceDiscoveryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, discovery: SoundCloudSourceDiscovery) -> None:
        self.connection.execute(
            """
            INSERT INTO soundcloud_source_discoveries (
                environment_id,
                song_id,
                track_url,
                track_urn,
                title,
                artist,
                description,
                purchase_title,
                purchase_url,
                downloadable,
                download_url,
                links_json,
                tags_json,
                release_metadata_json,
                warnings_json,
                raw_json,
                fetched_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(environment_id, song_id) DO UPDATE SET
                track_url = excluded.track_url,
                track_urn = excluded.track_urn,
                title = excluded.title,
                artist = excluded.artist,
                description = excluded.description,
                purchase_title = excluded.purchase_title,
                purchase_url = excluded.purchase_url,
                downloadable = excluded.downloadable,
                download_url = excluded.download_url,
                links_json = excluded.links_json,
                tags_json = excluded.tags_json,
                release_metadata_json = excluded.release_metadata_json,
                warnings_json = excluded.warnings_json,
                raw_json = excluded.raw_json,
                fetched_at = excluded.fetched_at
            """,
            (
                discovery.environment_id,
                discovery.song_id,
                discovery.track_url,
                discovery.track_urn,
                discovery.title,
                discovery.artist,
                discovery.description,
                discovery.purchase_title,
                discovery.purchase_url,
                _bool_to_int(discovery.downloadable),
                discovery.download_url,
                json.dumps(
                    [
                        {
                            "url": link.url,
                            "label": link.label,
                            "kind": link.kind,
                            "source": link.source,
                        }
                        for link in discovery.links
                    ],
                    sort_keys=True,
                ),
                json.dumps(list(discovery.tags), sort_keys=True),
                json.dumps(discovery.release_metadata, sort_keys=True),
                json.dumps(list(discovery.warnings), sort_keys=True),
                json.dumps(discovery.raw, sort_keys=True),
                discovery.fetched_at,
            ),
        )
        self.connection.commit()

    def get(self, environment_id: str, song_id: str) -> SoundCloudSourceDiscovery | None:
        row = self.connection.execute(
            """
            SELECT * FROM soundcloud_source_discoveries
            WHERE environment_id = ? AND song_id = ?
            """,
            (environment_id, song_id),
        ).fetchone()
        return _discovery_from_row(row)


def _discovery_from_row(row: sqlite3.Row | None) -> SoundCloudSourceDiscovery | None:
    if row is None:
        return None
    links = tuple(
        SoundCloudDiscoveryLink(
            url=str(item.get("url", "")),
            label=cast(str | None, item.get("label")),
            kind=str(item.get("kind", "external")),
            source=str(item.get("source", "stored")),
        )
        for item in _json_list(row["links_json"])
        if isinstance(item, dict) and item.get("url")
    )
    return SoundCloudSourceDiscovery(
        environment_id=cast(str, row["environment_id"]),
        song_id=cast(str, row["song_id"]),
        track_url=cast(str, row["track_url"]),
        track_urn=cast(str | None, row["track_urn"]),
        title=cast(str | None, row["title"]),
        artist=cast(str | None, row["artist"]),
        description=cast(str | None, row["description"]),
        purchase_title=cast(str | None, row["purchase_title"]),
        purchase_url=cast(str | None, row["purchase_url"]),
        downloadable=_int_to_bool(cast(int | None, row["downloadable"])),
        download_url=cast(str | None, row["download_url"]),
        links=links,
        tags=tuple(str(item) for item in _json_list(row["tags_json"])),
        release_metadata={
            str(key): str(value)
            for key, value in _json_dict(row["release_metadata_json"]).items()
        },
        warnings=tuple(str(item) for item in _json_list(row["warnings_json"])),
        raw=_json_dict(row["raw_json"]),
        fetched_at=cast(str, row["fetched_at"]),
    )


def _json_list(value: object) -> list[object]:
    if not isinstance(value, str):
        return []
    try:
        decoded = json.loads(value)
    except ValueError:
        return []
    return decoded if isinstance(decoded, list) else []


def _json_dict(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        return {}
    try:
        decoded = json.loads(value)
    except ValueError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _int_to_bool(value: int | None) -> bool | None:
    if value is None:
        return None
    return bool(value)
