from fastapi import APIRouter

from music_manager_backend.application.dtos import EnvironmentCreate
from music_manager_backend.application.use_cases.create_environment import CreateEnvironment
from music_manager_backend.infrastructure.persistence import InMemoryEnvironmentRepository

router = APIRouter(prefix="/environments", tags=["environments"])
repository = InMemoryEnvironmentRepository()


@router.get("")
def list_environments() -> list[dict[str, str]]:
    return [
        {"id": item.id, "name": item.name, "root_path": str(item.root_path)}
        for item in repository.list()
    ]


@router.post("")
def create_environment(data: EnvironmentCreate) -> dict[str, str]:
    environment = CreateEnvironment(repository).execute(data)
    return {"id": environment.id, "name": environment.name, "root_path": str(environment.root_path)}

