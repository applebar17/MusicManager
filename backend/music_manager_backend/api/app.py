import logging
import sqlite3
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response

from music_manager_backend.api.container import AppContainer
from music_manager_backend.api.logging_config import configure_logging
from music_manager_backend.api.operation_coordinator import OperationCoordinator
from music_manager_backend.api.routers import environments, health, library, playback
from music_manager_backend.infrastructure.persistence.migration_runner import upgrade_database
from music_manager_backend.infrastructure.soundcloud import (
    PublicPlaylistImporter,
    PublicTrackDiscoveryProvider,
)
from music_manager_backend.shared.errors import (
    DatabaseBusyError,
    InfrastructureError,
    MusicManagerError,
    NotFoundError,
    OperationInProgressError,
    ValidationError,
)
from music_manager_backend.shared.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, run_migrations: bool = True) -> FastAPI:
    resolved_settings = settings or get_settings()
    if run_migrations:
        upgrade_database(resolved_settings.database_path)
    configure_logging(resolved_settings)

    container = AppContainer(
        settings=resolved_settings,
        soundcloud_playlist_importer=PublicPlaylistImporter(),
        soundcloud_track_discovery_provider=PublicTrackDiscoveryProvider(),
        operation_coordinator=OperationCoordinator(),
    )

    app = FastAPI(title=resolved_settings.app_name)
    app.state.container = container
    app.add_exception_handler(NotFoundError, music_manager_not_found_handler)
    app.add_exception_handler(ValidationError, music_manager_validation_handler)
    app.add_exception_handler(OperationInProgressError, operation_in_progress_handler)
    app.add_exception_handler(DatabaseBusyError, database_busy_handler)
    app.add_exception_handler(InfrastructureError, music_manager_infrastructure_handler)
    app.add_exception_handler(sqlite3.OperationalError, sqlite_operational_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
    app.middleware("http")(request_logging_middleware)
    app.include_router(health.router)
    app.include_router(environments.router)
    app.include_router(library.router)
    app.include_router(playback.router)
    logger.info(
        "Started %s environment=%s database_path=%s log_file_path=%s",
        resolved_settings.app_name,
        resolved_settings.environment,
        resolved_settings.database_path,
        resolved_settings.log_file_path,
    )
    return app


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    request.state.request_id = request_id
    started_at = perf_counter()
    response = await call_next(request)
    duration_ms = (perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    log_method = logger.warning if response.status_code >= 500 else logger.info
    log_method(
        "API request request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


def music_manager_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(request, exc, status_code=404)


def operation_in_progress_handler(request: Request, exc: Exception) -> JSONResponse:
    response = _music_manager_error_response(request, exc, status_code=409)
    response.headers["Retry-After"] = "2"
    return response


def music_manager_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(request, exc, status_code=400)


def database_busy_handler(request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(request, exc, status_code=503)


def music_manager_infrastructure_handler(request: Request, exc: Exception) -> JSONResponse:
    return _music_manager_error_response(request, exc, status_code=502)


def sqlite_operational_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if _is_sqlite_busy_error(exc):
        logger.warning(
            "SQLite busy request_id=%s method=%s path=%s error=%s",
            _request_id(request),
            request.method,
            request.url.path,
            exc,
        )
        return _music_manager_error_response(
            request,
            DatabaseBusyError(
                "The local database is busy. Retry the request in a moment.",
                code="database_busy",
            ),
            status_code=503,
        )
    logger.error(
        "Unhandled SQLite error request_id=%s method=%s path=%s",
        _request_id(request),
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": "database_error",
            "message": "Unexpected database error. Check backend logs for details.",
        },
        headers=_response_headers(request),
    )


def request_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": "request_validation_error", "message": str(exc)},
        headers=_response_headers(request),
    )


def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled API error request_id=%s method=%s path=%s",
        _request_id(request),
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": "unexpected_error",
            "message": "Unexpected backend error. Check backend logs for details.",
        },
        headers=_response_headers(request),
    )


def _music_manager_error_response(
    request: Request,
    exc: Exception,
    *,
    status_code: int,
) -> JSONResponse:
    if not isinstance(exc, MusicManagerError):
        raise exc
    return JSONResponse(
        status_code=status_code,
        content=exc.to_detail().__dict__,
        headers=_response_headers(request),
    )


def _response_headers(request: Request) -> dict[str, str]:
    return {"X-Request-ID": _request_id(request)}


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _is_sqlite_busy_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "database is locked" in message or "database is busy" in message


app = create_app()
