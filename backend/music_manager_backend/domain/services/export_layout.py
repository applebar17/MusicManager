from pathlib import Path

from music_manager_backend.domain.entities import AudioFile, MusicEnvironment, Playlist, SongMaster
from music_manager_backend.domain.services.filename_sanitizer import sanitize_path_part, unique_path
from music_manager_backend.shared.errors import ValidationError

EXPORT_METADATA_FOLDER_NAME = ".music_manager"
EXPORT_MANIFEST_NAME = "export_manifest.json"


class ExportLayout:
    def __init__(self, environment: MusicEnvironment) -> None:
        self.environment = environment
        self.export_root = environment.root_path
        self.managed_root = self.export_root
        self.metadata_root = self.export_root / EXPORT_METADATA_FOLDER_NAME
        self.manifest_path = self.metadata_root / EXPORT_MANIFEST_NAME
        self.deprecated_folder = self.metadata_root / sanitize_path_part(
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
        folder = self.export_root / sanitize_path_part(playlist.display_name)
        unique_folder = self._ensure_export_root(unique_path(folder, self._used_playlist_folders))
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
        return self._ensure_export_root(unique_path(target, used_paths))

    def deprecated_target(self, *, song: SongMaster, audio_file: AudioFile) -> Path:
        filename = sanitize_path_part(f"{_artist(song)} - {song.display_title}")
        used_paths = self._used_track_paths.setdefault(self.deprecated_folder, set())
        return self._ensure_export_root(
            unique_path(self.deprecated_folder / f"{filename}{audio_file.path.suffix}", used_paths)
        )

    def _ensure_export_root(self, path: Path) -> Path:
        export_root = self.export_root.resolve(strict=False)
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(export_root):
            raise ValidationError(f"Export target path is outside environment root: {path}")
        return path


def _artist(song: SongMaster) -> str:
    return song.display_artist or "Unknown Artist"
