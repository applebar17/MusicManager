import sqlite3
from pathlib import Path

from music_manager_backend.infrastructure.persistence.migration_runner import upgrade_database

EXPECTED_TABLES = {
    "alembic_version",
    "audio_files",
    "environments",
    "export_apply_item_results",
    "export_apply_runs",
    "export_plan_items",
    "export_plans",
    "libraries",
    "library_alignment_items",
    "library_alignment_runs",
    "library_metadata_assets",
    "library_metadata_import_runs",
    "library_metadata_index_entries",
    "library_tracks",
    "match_links",
    "playlist_items",
    "playlists",
    "remote_playlists",
    "scan_runs",
    "songs",
    "song_library_links",
    "soundcloud_source_discoveries",
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

    assert version == ("0014",)
