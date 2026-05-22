from fastapi import FastAPI

from music_manager_backend.api.routers import environments, health


def create_app() -> FastAPI:
    app = FastAPI(title="Music Manager")
    app.include_router(health.router)
    app.include_router(environments.router)
    return app


app = create_app()

