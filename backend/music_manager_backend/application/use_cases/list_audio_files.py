from music_manager_backend.domain.entities import AudioFile
from music_manager_backend.domain.entities.audio_file import AudioFileStatus
from music_manager_backend.ports.repositories import AudioFileRepository, EnvironmentRepository
from music_manager_backend.shared.errors import NotFoundError, ValidationError


class ListAudioFiles:
    def __init__(
        self,
        environments: EnvironmentRepository,
        audio_files: AudioFileRepository,
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files

    def execute(self, environment_id: str, status: str = "active") -> list[AudioFile]:
        if self.environments.get(environment_id) is None:
            raise NotFoundError(f"Environment not found: {environment_id}")
        if status == "all":
            return self.audio_files.list_by_environment(environment_id)
        if status not in {"active", "removed"}:
            raise ValidationError(f"Unsupported audio file status: {status}")
        return self.audio_files.list_by_environment(environment_id, status=AudioFileStatus(status))
