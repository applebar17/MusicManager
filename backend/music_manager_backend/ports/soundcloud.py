from typing import Protocol

from music_manager_backend.domain.entities import RemotePlaylist


class SoundCloudPlaylistImporter(Protocol):
    def import_playlist(self, url: str) -> RemotePlaylist:
        pass

