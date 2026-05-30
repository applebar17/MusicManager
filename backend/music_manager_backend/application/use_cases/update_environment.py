from music_manager_backend.application.dtos import EnvironmentUpdate
from music_manager_backend.domain.entities import MusicEnvironment
from music_manager_backend.infrastructure.filesystem import validate_readable_directory
from music_manager_backend.ports.repositories import EnvironmentRepository
from music_manager_backend.shared.errors import NotFoundError


class UpdateEnvironment:
    def __init__(self, environments: EnvironmentRepository) -> None:
        self.environments = environments

    def execute(self, environment_id: str, data: EnvironmentUpdate) -> MusicEnvironment:
        current = self.environments.get(environment_id)
        if current is None:
            raise NotFoundError(f"Environment not found: {environment_id}")

        root_path = data.root_path if data.root_path is not None else current.root_path
        download_path = (
            data.download_path
            if "download_path" in data.model_fields_set
            else current.download_path
        )
        validate_readable_directory(root_path)
        if download_path is not None:
            validate_readable_directory(download_path)

        updated = MusicEnvironment(
            id=current.id,
            name=data.name if data.name is not None else current.name,
            root_path=root_path,
            download_path=download_path,
            deprecated_folder_name=(
                data.deprecated_folder_name
                if data.deprecated_folder_name is not None
                else current.deprecated_folder_name
            ),
            default_export_profile=current.default_export_profile,
            archived_at=current.archived_at,
        )
        self.environments.save(updated)
        return updated
