from pathlib import Path

from music_manager_backend.infrastructure.persistence.sqlite import (
    SQLITE_BUSY_TIMEOUT_MILLISECONDS,
    connect,
)


def test_connect_enables_sqlite_request_safety_pragmas(tmp_path: Path) -> None:
    database_path = tmp_path / "music.sqlite3"
    connection = connect(database_path)
    try:
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        connection.close()

    assert foreign_keys == 1
    assert busy_timeout == SQLITE_BUSY_TIMEOUT_MILLISECONDS
    assert journal_mode.lower() == "wal"
