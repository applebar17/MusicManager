from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from music_manager_backend.api.container import AppContainer
from music_manager_backend.api.routers import environments, health, playback
from music_manager_backend.infrastructure.persistence import (
    SqliteAudioFileRepository,
    SqliteEnvironmentRepository,
    SqliteMatchLinkRepository,
    SqlitePlaylistRepository,
    SqliteRemotePlaylistRepository,
    SqliteScanRunRepository,
    SqliteSongRepository,
    SqliteSyncSnapshotRepository,
)
from music_manager_backend.infrastructure.persistence.migration_runner import upgrade_database
from music_manager_backend.infrastructure.persistence.sqlite import connect
from music_manager_backend.infrastructure.soundcloud import PublicPlaylistImporter
from music_manager_backend.shared.errors import (
    InfrastructureError,
    MusicManagerError,
    NotFoundError,
    ValidationError,
)
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
        match_link_repository=SqliteMatchLinkRepository(connection),
        playlist_repository=SqlitePlaylistRepository(connection),
        remote_playlist_repository=SqliteRemotePlaylistRepository(connection),
        scan_run_repository=SqliteScanRunRepository(connection),
        song_repository=SqliteSongRepository(connection),
        sync_snapshot_repository=SqliteSyncSnapshotRepository(connection),
        soundcloud_playlist_importer=PublicPlaylistImporter(),
    )

    app = FastAPI(title=resolved_settings.app_name)
    app.state.container = container
    app.add_exception_handler(NotFoundError, music_manager_not_found_handler)
    app.add_exception_handler(ValidationError, music_manager_validation_handler)
    app.add_exception_handler(InfrastructureError, music_manager_infrastructure_handler)
    app.include_router(health.router)
    app.include_router(environments.router)
    app.include_router(playback.router)
    return app


def music_manager_not_found_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(exc, status_code=404)


def music_manager_validation_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(exc, status_code=400)


def music_manager_infrastructure_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(exc, status_code=502)


def _music_manager_error_response(exc: Exception, *, status_code: int) -> JSONResponse:
    if not isinstance(exc, MusicManagerError):
        raise exc
    return JSONResponse(status_code=status_code, content=exc.to_detail().__dict__)


app = create_app()
