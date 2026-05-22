from typing import Protocol

from music_manager_backend.domain.entities import AudioFile, MatchLink, SongMaster


class TrackMatcher(Protocol):
    def match(self, songs: list[SongMaster], files: list[AudioFile]) -> list[MatchLink]:
        pass

