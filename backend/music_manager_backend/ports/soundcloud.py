from typing import Protocol

from music_manager_backend.ports.soundcloud_models import ParsedSoundCloudPlaylist


class SoundCloudPlaylistImporter(Protocol):
    def import_playlist(self, url: str) -> ParsedSoundCloudPlaylist:
        pass


class SoundCloudHtmlFetcher(Protocol):
    def fetch(self, url: str) -> str:
        pass
