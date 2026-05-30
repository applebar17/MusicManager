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
                download_path,
                deprecated_folder_name,
                default_export_profile,
                archived_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                root_path = excluded.root_path,
                download_path = excluded.download_path,
                deprecated_folder_name = excluded.deprecated_folder_name,
                default_export_profile = excluded.default_export_profile,
                archived_at = excluded.archived_at
            """,
            (
                environment.id,
                environment.name,
                str(environment.root_path),
                str(environment.download_path) if environment.download_path is not None else None,
                environment.deprecated_folder_name,
                environment.default_export_profile,
                environment.archived_at,
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

    def list(self, *, include_archived: bool = False) -> list[MusicEnvironment]:
        if include_archived:
            rows = self.connection.execute(
                "SELECT * FROM environments ORDER BY name, id"
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM environments WHERE archived_at IS NULL ORDER BY name, id"
            ).fetchall()
        return [_environment_from_row(row) for row in rows]

    def archive(self, environment_id: str, archived_at: str) -> MusicEnvironment | None:
        self.connection.execute(
            "UPDATE environments SET archived_at = ? WHERE id = ?",
            (archived_at, environment_id),
        )
        self.connection.commit()
        return self.get(environment_id)


def _environment_from_row(row: sqlite3.Row) -> MusicEnvironment:
    download_path = cast(str | None, row["download_path"])
    return MusicEnvironment(
        id=cast(str, row["id"]),
        name=cast(str, row["name"]),
        root_path=Path(cast(str, row["root_path"])),
        download_path=Path(download_path) if download_path is not None else None,
        deprecated_folder_name=cast(str, row["deprecated_folder_name"]),
        default_export_profile=cast(str, row["default_export_profile"]),
        archived_at=cast(str | None, row["archived_at"]),
    )
