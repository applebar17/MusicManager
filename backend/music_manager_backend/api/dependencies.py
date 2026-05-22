from typing import cast

from fastapi import Request

from music_manager_backend.api.container import AppContainer
from music_manager_backend.ports.repositories import EnvironmentRepository


def get_container(request: Request) -> AppContainer:
    return cast(AppContainer, request.app.state.container)


def get_environment_repository(request: Request) -> EnvironmentRepository:
    return get_container(request).environment_repository
