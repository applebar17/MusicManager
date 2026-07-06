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
            INSERT INTO export_plans (
                id,
                environment_id,
                locked_at,
                validation_error_code,
                validation_error_message
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                environment_id = excluded.environment_id,
                locked_at = excluded.locked_at,
                validation_error_code = excluded.validation_error_code,
                validation_error_message = excluded.validation_error_message
            """,
            (
                export_plan.id,
                export_plan.environment_id,
                export_plan.locked_at,
                export_plan.validation_error_code,
                export_plan.validation_error_message,
            ),
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
                    public_id,
                    action,
                    target_path,
                    source_path,
                    reason,
                    metadata_payload_json,
                    included,
                    validation_error_code,
                    validation_error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    export_plan.id,
                    position,
                    item.id,
                    item.action.value,
                    str(item.target_path),
                    str(item.source_path) if item.source_path is not None else None,
                    item.reason,
                    item.metadata_payload_json,
                    int(item.included),
                    item.validation_error_code,
                    item.validation_error_message,
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
            locked_at=cast(str | None, row["locked_at"]),
            validation_error_code=cast(str | None, row["validation_error_code"]),
            validation_error_message=cast(str | None, row["validation_error_message"]),
        )


def _export_plan_item_from_row(row: sqlite3.Row) -> ExportPlanItem:
    source_path = cast(str | None, row["source_path"])
    return ExportPlanItem(
        action=ExportAction(cast(str, row["action"])),
        target_path=Path(cast(str, row["target_path"])),
        source_path=Path(source_path) if source_path is not None else None,
        reason=cast(str | None, row["reason"]),
        metadata_payload_json=cast(str | None, row["metadata_payload_json"]),
        id=cast(str, row["public_id"]),
        included=bool(cast(int, row["included"])),
        validation_error_code=cast(str | None, row["validation_error_code"]),
        validation_error_message=cast(str | None, row["validation_error_message"]),
    )
