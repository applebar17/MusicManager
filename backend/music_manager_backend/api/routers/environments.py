from typing import Annotated

from fastapi import APIRouter, Depends

from music_manager_backend.api.dependencies import get_environment_repository
from music_manager_backend.application.dtos import EnvironmentCreate
from music_manager_backend.application.use_cases.create_environment import CreateEnvironment
from music_manager_backend.ports.repositories import EnvironmentRepository

router = APIRouter(prefix="/environments", tags=["environments"])
EnvironmentRepositoryDependency = Annotated[
    EnvironmentRepository,
    Depends(get_environment_repository),
]


@router.get("")
def list_environments(
    repository: EnvironmentRepositoryDependency,
) -> list[dict[str, str]]:
    return [
        {"id": item.id, "name": item.name, "root_path": str(item.root_path)}
        for item in repository.list()
    ]


@router.post("")
def create_environment(
    data: EnvironmentCreate,
    repository: EnvironmentRepositoryDependency,
) -> dict[str, str]:
    environment = CreateEnvironment(repository).execute(data)
    return {"id": environment.id, "name": environment.name, "root_path": str(environment.root_path)}
