from music_manager_backend.domain.entities import AudioFile, MatchLink, SongMaster
from music_manager_backend.ports.matching import TrackMatcher


class MatchSongs:
    def __init__(self, matcher: TrackMatcher) -> None:
        self.matcher = matcher

    def execute(self, songs: list[SongMaster], files: list[AudioFile]) -> list[MatchLink]:
        return self.matcher.match(songs, files)

