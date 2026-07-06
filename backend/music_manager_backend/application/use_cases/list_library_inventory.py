from music_manager_backend.application.dtos import (
    LibraryMetadataAssetRead,
    LibraryMetadataIndexEntryRead,
    LibraryTrackRead,
    library_metadata_asset_read,
    library_metadata_index_entry_read,
    library_track_read,
)
from music_manager_backend.ports.repositories import (
    LibraryMetadataRepository,
    LibraryRepository,
    LibraryTrackRepository,
    SongLibraryLinkRepository,
)
from music_manager_backend.shared.errors import ValidationError


class ListLibraryTracks:
    def __init__(
        self,
        libraries: LibraryRepository,
        library_tracks: LibraryTrackRepository,
        song_library_links: SongLibraryLinkRepository,
    ) -> None:
        self.libraries = libraries
        self.library_tracks = library_tracks
        self.song_library_links = song_library_links

    def execute(self) -> list[LibraryTrackRead]:
        library = self.libraries.get_default()
        if library is None:
            raise ValidationError("Shared library is not configured.")

        tracks = self.library_tracks.list(library.id)
        mapped_counts = self.song_library_links.count_by_library_track_ids(
            {track.id for track in tracks},
        )
        return [
            library_track_read(
                track,
                mapped_song_count=mapped_counts.get(track.id, 0),
            )
            for track in tracks
        ]


class ListLibraryMetadataAssets:
    def __init__(
        self,
        libraries: LibraryRepository,
        metadata_repository: LibraryMetadataRepository,
    ) -> None:
        self.libraries = libraries
        self.metadata_repository = metadata_repository

    def execute(self) -> list[LibraryMetadataAssetRead]:
        library = self.libraries.get_default()
        if library is None:
            raise ValidationError("Shared library is not configured.")
        return [
            library_metadata_asset_read(asset)
            for asset in self.metadata_repository.list_assets(library.id)
        ]


class ListLibraryMetadataIndexEntries:
    def __init__(
        self,
        libraries: LibraryRepository,
        metadata_repository: LibraryMetadataRepository,
    ) -> None:
        self.libraries = libraries
        self.metadata_repository = metadata_repository

    def execute(self) -> list[LibraryMetadataIndexEntryRead]:
        library = self.libraries.get_default()
        if library is None:
            raise ValidationError("Shared library is not configured.")
        return [
            library_metadata_index_entry_read(entry)
            for entry in self.metadata_repository.list_index_entries(library.id)
        ]
