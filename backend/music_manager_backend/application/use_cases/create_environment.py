from music_manager_backend.application.dtos import EnvironmentCreate
from music_manager_backend.domain.entities import MusicEnvironment
from music_manager_backend.infrastructure.filesystem import validate_readable_directory
from music_manager_backend.ports.repositories import EnvironmentRepository
from music_manager_backend.shared.ids import new_id


class CreateEnvironment:
    def __init__(self, environments: EnvironmentRepository) -> None:
        self.environments = environments

    def execute(self, data: EnvironmentCreate) -> MusicEnvironment:
        validate_readable_directory(data.root_path)
        if data.download_path is not None:
            validate_readable_directory(data.download_path)
        environment = MusicEnvironment(
            id=new_id("env"),
            name=data.name,
            root_path=data.root_path,
            download_path=data.download_path,
            deprecated_folder_name=data.deprecated_folder_name,
        )
        self.environments.save(environment)
        return environment
