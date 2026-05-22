import sqlite3
from pathlib import Path

from music_manager_backend.infrastructure.persistence.migration_runner import upgrade_database

EXPECTED_TABLES = {
    "alembic_version",
    "audio_files",
    "environments",
    "export_plan_items",
    "export_plans",
    "match_links",
    "playlist_items",
    "playlists",
    "remote_playlists",
    "scan_runs",
    "songs",
    "sync_snapshots",
}


def test_migrations_create_expected_tables(database_path: Path) -> None:
    upgrade_database(database_path)

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()

    assert {row[0] for row in rows} >= EXPECTED_TABLES


def test_migrations_are_idempotent(database_path: Path) -> None:
    upgrade_database(database_path)
    upgrade_database(database_path)

    with sqlite3.connect(database_path) as connection:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()

    assert version == ("0003",)
