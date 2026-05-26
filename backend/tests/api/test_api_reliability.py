import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient

from music_manager_backend.api.app import create_app
from music_manager_backend.api.container import SqliteRepositoryBundle
from music_manager_backend.api.dependencies import get_repository_bundle
from music_manager_backend.shared.settings import Settings


def test_request_scoped_repositories_use_fresh_closed_connections(
    api_settings: Settings,
) -> None:
    app = create_app(api_settings)
    connections: list[sqlite3.Connection] = []

    RepositoryBundleDependency = Annotated[
        SqliteRepositoryBundle,
        Depends(get_repository_bundle),
    ]

    @app.get("/debug/connection")
    def connection_debug(repositories: RepositoryBundleDependency) -> dict[str, str]:
        connections.append(repositories.connection)
        return {"status": "ok"}

    client = TestClient(app)

    first = client.get("/debug/connection")
    second = client.get("/debug/connection")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(connections) == 2
    assert connections[0] is not connections[1]
    for connection in connections:
        try:
            connection.execute("SELECT 1")
        except sqlite3.ProgrammingError as exc:
            assert "closed" in str(exc).lower()
        else:
            raise AssertionError("Request-scoped SQLite connection was not closed")


def test_unexpected_errors_include_request_id_and_log_stack_trace(
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "logs" / "backend.log"
    app = create_app(
        Settings(
            environment="test",
            database_path=tmp_path / "music.sqlite3",
            log_file_path=log_file,
        )
    )

    @app.get("/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom", headers={"X-Request-ID": "request-123"})

    assert response.status_code == 500
    assert response.json()["code"] == "unexpected_error"
    assert response.headers["X-Request-ID"] == "request-123"
    log_text = log_file.read_text(encoding="utf-8")
    assert "request-123" in log_text
    assert "RuntimeError: boom" in log_text


def test_sqlite_busy_errors_return_retryable_503(api_settings: Settings) -> None:
    app = create_app(api_settings)

    @app.get("/locked")
    def locked() -> dict[str, str]:
        raise sqlite3.OperationalError("database is locked")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/locked")

    assert response.status_code == 503
    assert response.json() == {
        "code": "database_busy",
        "message": "The local database is busy. Retry the request in a moment.",
    }
    assert response.headers["X-Request-ID"]
