from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from music_manager_backend.api.container import AppContainer
from music_manager_backend.api.routers import environments, health
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteScanRunRepository,
)
from music_manager_backend.infrastructure.persistence.migration_runner import upgrade_database
from music_manager_backend.infrastructure.persistence.sqlite import connect
from music_manager_backend.shared.errors import MusicManagerError, NotFoundError, ValidationError
from music_manager_backend.shared.settings import Settings, get_settings


def create_app(settings: Settings | None = None, *, run_migrations: bool = True) -> FastAPI:
    resolved_settings = settings or get_settings()
    if run_migrations:
        upgrade_database(resolved_settings.database_path)

    connection = connect(resolved_settings.database_path)
    container = AppContainer(
        settings=resolved_settings,
        audio_file_repository=SqliteAudioFileRepository(connection),
        environment_repository=SqliteEnvironmentRepository(connection),
        scan_run_repository=SqliteScanRunRepository(connection),
    )

    app = FastAPI(title=resolved_settings.app_name)
    app.state.container = container
    app.add_exception_handler(NotFoundError, music_manager_not_found_handler)
    app.add_exception_handler(ValidationError, music_manager_validation_handler)
    app.include_router(health.router)
    app.include_router(environments.router)
    return app


def music_manager_not_found_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(exc, status_code=404)


def music_manager_validation_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(exc, status_code=400)


def _music_manager_error_response(exc: Exception, *, status_code: int) -> JSONResponse:
    if not isinstance(exc, MusicManagerError):
        raise exc
    return JSONResponse(status_code=status_code, content=exc.to_detail().__dict__)


app = create_app()
