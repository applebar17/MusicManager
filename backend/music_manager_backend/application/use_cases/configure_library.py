from music_manager_backend.application.dtos.library import (
    LibraryConfigure,
    LibraryRead,
    library_read,
)
from music_manager_backend.domain.entities.library import DEFAULT_LIBRARY_ID, MusicLibrary
from music_manager_backend.infrastructure.filesystem import validate_writable_directory
from music_manager_backend.ports.repositories import LibraryRepository, LibraryTrackRepository
from music_manager_backend.shared.time import utc_now_iso


class ConfigureLibrary:
    def __init__(
        self,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
    ) -> None:
        self.libraries = libraries
        self.library_tracks = library_tracks

    def execute(self, data: LibraryConfigure) -> LibraryRead:
        root_path = validate_writable_directory(data.root_path)
        existing = self.libraries.get_default()
        now = utc_now_iso()
        library = MusicLibrary(
            id=DEFAULT_LIBRARY_ID,
            root_path=root_path,
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        self.libraries.save_default(library)
        return library_read(
            library,
            track_count=self.library_tracks.count(library.id),
        )
