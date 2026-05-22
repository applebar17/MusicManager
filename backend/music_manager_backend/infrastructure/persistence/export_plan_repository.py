import sqlite3
from pathlib import Path
from typing import cast

from music_manager_backend.domain.entities import ExportPlan, ExportPlanItem
from music_manager_backend.domain.entities.export_plan import ExportAction


class SqliteExportPlanRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, export_plan: ExportPlan) -> None:
        self.connection.execute(
            """
            INSERT INTO export_plans (id, environment_id)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET
                environment_id = excluded.environment_id
            """,
            (export_plan.id, export_plan.environment_id),
        )
        self.connection.execute(
            "DELETE FROM export_plan_items WHERE export_plan_id = ?",
            (export_plan.id,),
        )
        for position, item in enumerate(export_plan.items):
            self.connection.execute(
                """
                INSERT INTO export_plan_items (
                    export_plan_id,
                    position,
                    action,
                    target_path,
                    source_path,
                    reason
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    export_plan.id,
                    position,
                    item.action.value,
                    str(item.target_path),
                    str(item.source_path) if item.source_path is not None else None,
                    item.reason,
                ),
            )
        self.connection.commit()

    def get(self, export_plan_id: str) -> ExportPlan | None:
        row = self.connection.execute(
            "SELECT * FROM export_plans WHERE id = ?",
            (export_plan_id,),
        ).fetchone()
        if row is None:
            return None

        item_rows = self.connection.execute(
            """
            SELECT * FROM export_plan_items
            WHERE export_plan_id = ?
            ORDER BY position
            """,
            (export_plan_id,),
        ).fetchall()
        return ExportPlan(
            id=cast(str, row["id"]),
            environment_id=cast(str, row["environment_id"]),
            items=tuple(_export_plan_item_from_row(item_row) for item_row in item_rows),
        )


def _export_plan_item_from_row(row: sqlite3.Row) -> ExportPlanItem:
    source_path = cast(str | None, row["source_path"])
    return ExportPlanItem(
        action=ExportAction(cast(str, row["action"])),
        target_path=Path(cast(str, row["target_path"])),
        source_path=Path(source_path) if source_path is not None else None,
        reason=cast(str | None, row["reason"]),
    )
