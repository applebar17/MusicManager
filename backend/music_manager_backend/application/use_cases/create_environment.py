from music_manager_backend.application.dtos import EnvironmentCreate
from music_manager_backend.domain.entities import MusicEnvironment
from music_manager_backend.ports.repositories import EnvironmentRepository
from music_manager_backend.shared.ids import new_id


class CreateEnvironment:
    def __init__(self, environments: EnvironmentRepository) -> None:
        self.environments = environments

    def execute(self, data: EnvironmentCreate) -> MusicEnvironment:
        environment = MusicEnvironment(
            id=new_id("env"),
            name=data.name,
            root_path=data.root_path,
            deprecated_folder_name=data.deprecated_folder_name,
        )
        self.environments.save(environment)
        return environment

