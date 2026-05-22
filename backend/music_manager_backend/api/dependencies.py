from typing import cast

from fastapi import Request

from music_manager_backend.api.container import AppContainer
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    ScanRunRepository,
)


def get_container(request: Request) -> AppContainer:
    return cast(AppContainer, request.app.state.container)


def get_environment_repository(request: Request) -> EnvironmentRepository:
    return get_container(request).environment_repository


def get_audio_file_repository(request: Request) -> AudioFileRepository:
    return get_container(request).audio_file_repository


def get_scan_run_repository(request: Request) -> ScanRunRepository:
    return get_container(request).scan_run_repository
