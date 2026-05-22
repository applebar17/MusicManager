from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, MusicEnvironment, Playlist, SongMaster
from music_manager_backend.domain.services.filename_sanitizer import sanitize_path_part, unique_path
from music_manager_backend.shared.errors import ValidationError

MANAGED_EXPORT_FOLDER_NAME = "_music_manager_export"


class ExportLayout:
    def __init__(self, environment: MusicEnvironment) -> None:
        self.environment = environment
        self.managed_root = environment.root_path / MANAGED_EXPORT_FOLDER_NAME
        self.deprecated_folder = self.managed_root / sanitize_path_part(
            environment.deprecated_folder_name,
            fallback="_deprecated",
        )
        self._used_playlist_folders: set[Path] = set()
        self._playlist_folders: dict[str, Path] = {}
        self._used_track_paths: dict[Path, set[Path]] = {}

    def playlist_folder(self, playlist: Playlist) -> Path:
        cached = self._playlist_folders.get(playlist.id)
        if cached is not None:
            return cached
        folder = self.managed_root / sanitize_path_part(playlist.display_name)
        unique_folder = self._ensure_managed(unique_path(folder, self._used_playlist_folders))
        self._playlist_folders[playlist.id] = unique_folder
        return unique_folder

    def track_target(
        self,
        *,
        folder: Path,
        position: int,
        song: SongMaster,
        audio_file: AudioFile,
    ) -> Path:
        filename = sanitize_path_part(
            f"{position:03d} - {_artist(song)} - {song.display_title}",
        )
        target = folder / f"{filename}{audio_file.path.suffix}"
        used_paths = self._used_track_paths.setdefault(folder, set())
        return self._ensure_managed(unique_path(target, used_paths))

    def deprecated_target(self, *, song: SongMaster, audio_file: AudioFile) -> Path:
        filename = sanitize_path_part(f"{_artist(song)} - {song.display_title}")
        used_paths = self._used_track_paths.setdefault(self.deprecated_folder, set())
        return self._ensure_managed(
            unique_path(self.deprecated_folder / f"{filename}{audio_file.path.suffix}", used_paths)
        )

    def _ensure_managed(self, path: Path) -> Path:
        managed_root = self.managed_root.resolve(strict=False)
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(managed_root):
            raise ValidationError(f"Export target path is outside managed export root: {path}")
        return path


def _artist(song: SongMaster) -> str:
    return song.display_artist or "Unknown Artist"
