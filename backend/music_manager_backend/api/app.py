from fastapi import FastAPI

from music_manager_backend.api.container import AppContainer
from music_manager_backend.api.routers import environments, health
from music_manager_backend.infrastructure.persistence import SqliteEnvironmentRepository
from music_manager_backend.infrastructure.persistence.migration_runner import upgrade_database
from music_manager_backend.infrastructure.persistence.sqlite import connect
from music_manager_backend.shared.settings import Settings, get_settings


def create_app(settings: Settings | None = None, *, run_migrations: bool = True) -> FastAPI:
    resolved_settings = settings or get_settings()
    if run_migrations:
        upgrade_database(resolved_settings.database_path)

    connection = connect(resolved_settings.database_path)
    container = AppContainer(
        settings=resolved_settings,
        environment_repository=SqliteEnvironmentRepository(connection),
    )

    app = FastAPI(title=resolved_settings.app_name)
    app.state.container = container
    app.include_router(health.router)
    app.include_router(environments.router)
    return app


app = create_app()
