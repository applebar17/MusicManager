import sqlite3
from pathlib import Path

SQLITE_TIMEOUT_SECONDS = 30.0
SQLITE_BUSY_TIMEOUT_MILLISECONDS = 30_000


def connect(database_path: Path) -> sqlite3.Connection:
    if database_path != Path(":memory:"):
        database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        database_path,
        timeout=SQLITE_TIMEOUT_SECONDS,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MILLISECONDS}")
    if database_path != Path(":memory:"):
        connection.execute("PRAGMA journal_mode = WAL")
    return connection
