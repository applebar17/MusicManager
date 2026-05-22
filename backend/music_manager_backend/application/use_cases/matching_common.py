from dataclasses import dataclass

from music_manager_backend.domain.entities import (
    AudioFile,
    AudioFileStatus,
    MatchCandidate,
    SongMaster,
)
from music_manager_backend.ports.repositories import (
    AudioFileRepository,
    EnvironmentRepository,
    PlaylistRepository,
    SongRepository,
)
from music_manager_backend.shared.errors import NotFoundError


@dataclass(frozen=True)
class EnvironmentSongs:
    songs: list[SongMaster]
    song_ids: set[str]


def load_environment_songs(
    *,
    environment_id: str,
    environments: EnvironmentRepository,
    playlists: PlaylistRepository,
    songs: SongRepository,
) -> EnvironmentSongs:
    environment = environments.get(environment_id)
    if environment is None:
        raise NotFoundError(f"Environment not found: {environment_id}")

    seen_song_ids: set[str] = set()
    loaded: list[SongMaster] = []
    for playlist in playlists.list_by_environment(environment_id):
        for item in playlist.items:
            if item.song_id in seen_song_ids:
                continue
            song = songs.get(item.song_id)
            if song is None:
                continue
            seen_song_ids.add(item.song_id)
            loaded.append(song)
    return EnvironmentSongs(songs=loaded, song_ids=seen_song_ids)


def active_audio_files_by_id(
    *, environment_id: str, audio_files: AudioFileRepository
) -> dict[str, AudioFile]:
    return {
        audio_file.id: audio_file
        for audio_file in audio_files.list_by_environment(
            environment_id, status=AudioFileStatus.ACTIVE
        )
    }


def candidate_audio_file(
    candidate: MatchCandidate, active_files: dict[str, AudioFile]
) -> AudioFile | None:
    return active_files.get(candidate.audio_file_id)
