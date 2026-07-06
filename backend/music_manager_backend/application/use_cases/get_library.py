from music_manager_backend.application.dtos.library import LibraryRead, library_read
from music_manager_backend.domain.entities.library import DEFAULT_LIBRARY_ID
from music_manager_backend.domain.entities.library import LibraryTrackStatus
from music_manager_backend.ports.repositories import LibraryRepository, LibraryTrackRepository


class GetLibrary:
    def __init__(
        self,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
    ) -> None:
        self.libraries = libraries
        self.library_tracks = library_tracks

    def execute(self) -> LibraryRead:
        library = self.libraries.get_default()
        track_count = (
            self.library_tracks.count(library.id)
            if library is not None
            else self.library_tracks.count(DEFAULT_LIBRARY_ID)
        )
        missing_track_count = (
            self.library_tracks.count_by_status(library.id, LibraryTrackStatus.MISSING)
            if library is not None
            else self.library_tracks.count_by_status(DEFAULT_LIBRARY_ID, LibraryTrackStatus.MISSING)
        )
        return library_read(
            library,
            track_count=track_count,
            missing_track_count=missing_track_count,
        )
