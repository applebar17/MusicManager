import sqlite3
from pathlib import Path
from typing import cast

from music_manager_backend.domain.entities import MusicEnvironment


class SqliteEnvironmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, environment: MusicEnvironment) -> None:
        self.connection.execute(
            """
            INSERT INTO environments (
                id,
                name,
                root_path,
                deprecated_folder_name,
                default_export_profile
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                root_path = excluded.root_path,
                deprecated_folder_name = excluded.deprecated_folder_name,
                default_export_profile = excluded.default_export_profile
            """,
            (
                environment.id,
                environment.name,
                str(environment.root_path),
                environment.deprecated_folder_name,
                environment.default_export_profile,
            ),
        )
        self.connection.commit()

    def get(self, environment_id: str) -> MusicEnvironment | None:
        row = self.connection.execute(
            "SELECT * FROM environments WHERE id = ?",
            (environment_id,),
        ).fetchone()
        if row is None:
            return None
        return _environment_from_row(row)

    def list(self) -> list[MusicEnvironment]:
        rows = self.connection.execute("SELECT * FROM environments ORDER BY name, id").fetchall()
        return [_environment_from_row(row) for row in rows]


def _environment_from_row(row: sqlite3.Row) -> MusicEnvironment:
    return MusicEnvironment(
        id=cast(str, row["id"]),
        name=cast(str, row["name"]),
        root_path=Path(cast(str, row["root_path"])),
        deprecated_folder_name=cast(str, row["deprecated_folder_name"]),
        default_export_profile=cast(str, row["default_export_profile"]),
    )
