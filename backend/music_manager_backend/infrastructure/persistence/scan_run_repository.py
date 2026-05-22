import sqlite3
from typing import cast

from music_manager_backend.domain.entities import ScanRun


class SqliteScanRunRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, scan_run: ScanRun) -> None:
        self.connection.execute(
            """
            INSERT INTO scan_runs (
                id,
                environment_id,
                started_at,
                finished_at,
                added_count,
                changed_count,
                removed_count,
                moved_count,
                unchanged_count,
                total_active_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                environment_id = excluded.environment_id,
                started_at = excluded.started_at,
                finished_at = excluded.finished_at,
                added_count = excluded.added_count,
                changed_count = excluded.changed_count,
                removed_count = excluded.removed_count,
                moved_count = excluded.moved_count,
                unchanged_count = excluded.unchanged_count,
                total_active_count = excluded.total_active_count
            """,
            (
                scan_run.id,
                scan_run.environment_id,
                scan_run.started_at,
                scan_run.finished_at,
                scan_run.added_count,
                scan_run.changed_count,
                scan_run.removed_count,
                scan_run.moved_count,
                scan_run.unchanged_count,
                scan_run.total_active_count,
            ),
        )
        self.connection.commit()

    def get(self, scan_run_id: str) -> ScanRun | None:
        row = self.connection.execute(
            "SELECT * FROM scan_runs WHERE id = ?",
            (scan_run_id,),
        ).fetchone()
        if row is None:
            return None
        return ScanRun(
            id=cast(str, row["id"]),
            environment_id=cast(str, row["environment_id"]),
            started_at=cast(str, row["started_at"]),
            finished_at=cast(str | None, row["finished_at"]),
            added_count=cast(int, row["added_count"]),
            changed_count=cast(int, row["changed_count"]),
            removed_count=cast(int, row["removed_count"]),
            moved_count=cast(int, row["moved_count"]),
            unchanged_count=cast(int, row["unchanged_count"]),
            total_active_count=cast(int, row["total_active_count"]),
        )
