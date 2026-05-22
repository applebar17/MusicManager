from music_manager_backend.domain.entities import RemotePlaylist
from music_manager_backend.shared.ids import new_id


class PublicPlaylistImporter:
    def import_playlist(self, url: str) -> RemotePlaylist:
        return RemotePlaylist(
            id=new_id("remote_playlist"),
            source="soundcloud",
            source_url=url,
            name=url,
        )
