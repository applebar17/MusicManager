from typing import Annotated

from fastapi import APIRouter, Depends

from music_manager_backend.api.container import AppContainer
from music_manager_backend.api.dependencies import get_container

router = APIRouter(tags=["health"])
ContainerDependency = Annotated[AppContainer, Depends(get_container)]


@router.get("/health")
def health(container: ContainerDependency) -> dict[str, str]:
    try:
        with container.repository_bundle() as repositories:
            repositories.connection.execute("SELECT 1").fetchone()
    except Exception:
        return {"status": "degraded", "database": "error"}
    return {"status": "ok", "database": "ok"}
