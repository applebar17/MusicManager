from music_manager_backend.domain.entities import AudioFile
from music_manager_backend.ports.repositories import AudioFileRepository, EnvironmentRepository
from music_manager_backend.shared.errors import NotFoundError


class ListUnmanagedFiles:
    def __init__(
        self,
        environments: EnvironmentRepository,
        audio_files: AudioFileRepository,
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files

    def execute(self, environment_id: str) -> list[AudioFile]:
        if self.environments.get(environment_id) is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        return self.audio_files.list_unmanaged_active_by_environment(environment_id)
