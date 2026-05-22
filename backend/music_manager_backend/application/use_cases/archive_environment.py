from music_manager_backend.domain.entities import MusicEnvironment
from music_manager_backend.ports.repositories import EnvironmentRepository
from music_manager_backend.shared.errors import NotFoundError
from music_manager_backend.shared.time import utc_now_iso


class ArchiveEnvironment:
    def __init__(self, environments: EnvironmentRepository) -> None:
        self.environments = environments

    def execute(self, environment_id: str) -> MusicEnvironment:
        environment = self.environments.archive(environment_id, utc_now_iso())
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        return environment
