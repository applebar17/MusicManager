from dataclasses import dataclass
from pathlib import Path

from music_manager_backend.domain.entities import AudioFileStatus
from music_manager_backend.infrastructure.filesystem import validate_readable_file_inside_root
from music_manager_backend.ports.repositories import AudioFileRepository, EnvironmentRepository
from music_manager_backend.shared.errors import NotFoundError, ValidationError


@dataclass(frozen=True)
class PlaybackFile:
    path: Path
    filename: str


class GetPlaybackFile:
    def __init__(
        self,
        *,
        environments: EnvironmentRepository,
        audio_files: AudioFileRepository,
    ) -> None:
        self.environments = environments
        self.audio_files = audio_files

    def execute(self, environment_id: str, audio_file_id: str) -> PlaybackFile:
        environment = self.environments.get(environment_id)
        if environment is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        audio_file = self.audio_files.get(audio_file_id)
        if audio_file is None or audio_file.environment_id != environment_id:
            raise NotFoundError(f"Audio file not found: {audio_file_id}")
        if audio_file.status != AudioFileStatus.ACTIVE:
            raise ValidationError(f"Audio file is not active: {audio_file_id}")
        if not audio_file.path.exists():
            raise NotFoundError(f"Playback file not found: {audio_file.path}")

        path = validate_readable_file_inside_root(audio_file.path, environment.root_path)
        return PlaybackFile(path=path, filename=path.name)
