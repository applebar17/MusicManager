import sqlite3
from pathlib import Path
from typing import cast

from music_manager_backend.domain.entities import (
    ExportApplyItemResult,
    ExportApplyItemStatus,
    ExportApplyRun,
    ExportApplyRunStatus,
)
from music_manager_backend.domain.entities.export_plan import ExportAction


class SqliteExportApplyRunRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, apply_run: ExportApplyRun) -> None:
        self.connection.execute(
            """
            INSERT INTO export_apply_runs (
                id,
                export_plan_id,
                environment_id,
                status,
                started_at,
                finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                export_plan_id = excluded.export_plan_id,
                environment_id = excluded.environment_id,
                status = excluded.status,
                started_at = excluded.started_at,
                finished_at = excluded.finished_at
            """,
            (
                apply_run.id,
                apply_run.export_plan_id,
                apply_run.environment_id,
                apply_run.status.value,
                apply_run.started_at,
                apply_run.finished_at,
            ),
        )
        self.connection.execute(
            "DELETE FROM export_apply_item_results WHERE apply_run_id = ?",
            (apply_run.id,),
        )
        for position, result in enumerate(apply_run.item_results):
            self.connection.execute(
                """
                INSERT INTO export_apply_item_results (
                    apply_run_id,
                    position,
                    export_plan_item_id,
                    action,
                    source_path,
                    target_path,
                    status,
                    error_code,
                    error_message,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    apply_run.id,
                    position,
                    result.export_plan_item_id,
                    result.action.value,
                    str(result.source_path) if result.source_path is not None else None,
                    str(result.target_path),
                    result.status.value,
                    result.error_code,
                    result.error_message,
                    result.created_at,
                ),
            )
        self.connection.commit()

    def get(self, apply_run_id: str) -> ExportApplyRun | None:
        row = self.connection.execute(
            "SELECT * FROM export_apply_runs WHERE id = ?",
            (apply_run_id,),
        ).fetchone()
        if row is None:
            return None

        result_rows = self.connection.execute(
            """
            SELECT * FROM export_apply_item_results
            WHERE apply_run_id = ?
            ORDER BY position
            """,
            (apply_run_id,),
        ).fetchall()
        return ExportApplyRun(
            id=cast(str, row["id"]),
            export_plan_id=cast(str, row["export_plan_id"]),
            environment_id=cast(str, row["environment_id"]),
            status=ExportApplyRunStatus(cast(str, row["status"])),
            started_at=cast(str, row["started_at"]),
            finished_at=cast(str | None, row["finished_at"]),
            item_results=tuple(_apply_item_result_from_row(item_row) for item_row in result_rows),
        )


def _apply_item_result_from_row(row: sqlite3.Row) -> ExportApplyItemResult:
    source_path = cast(str | None, row["source_path"])
    return ExportApplyItemResult(
        action=ExportAction(cast(str, row["action"])),
        export_plan_item_id=cast(str | None, row["export_plan_item_id"]),
        source_path=Path(source_path) if source_path is not None else None,
        target_path=Path(cast(str, row["target_path"])),
        status=ExportApplyItemStatus(cast(str, row["status"])),
        error_code=cast(str | None, row["error_code"]),
        error_message=cast(str | None, row["error_message"]),
        created_at=cast(str, row["created_at"]),
    )
