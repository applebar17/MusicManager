import mimetypes
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from music_manager_backend.api.dependencies import (
    get_audio_file_repository,
    get_environment_repository,
)
from music_manager_backend.application.use_cases.get_playback_file import GetPlaybackFile
from music_manager_backend.ports.repositories import AudioFileRepository, EnvironmentRepository

router = APIRouter(
    prefix="/environments/{environment_id}/playback",
    tags=["playback"],
)
EnvironmentRepositoryDependency = Annotated[
    EnvironmentRepository,
    Depends(get_environment_repository),
]
AudioFileRepositoryDependency = Annotated[
    AudioFileRepository,
    Depends(get_audio_file_repository),
]


@router.get("/audio-files/{audio_file_id}")
def stream_audio_file(
    environment_id: str,
    audio_file_id: str,
    environments: EnvironmentRepositoryDependency,
    audio_files: AudioFileRepositoryDependency,
) -> FileResponse:
    playback_file = GetPlaybackFile(
        environments=environments,
        audio_files=audio_files,
    ).execute(environment_id, audio_file_id)
    media_type = mimetypes.guess_type(playback_file.path.name)[0] or "application/octet-stream"
    return FileResponse(
        playback_file.path,
        media_type=media_type,
        filename=playback_file.filename,
    )
