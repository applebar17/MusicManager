from music_manager_backend.domain.entities import MusicEnvironment


class InMemoryEnvironmentRepository:
    def __init__(self) -> None:
        self._items: dict[str, MusicEnvironment] = {}

    def save(self, environment: MusicEnvironment) -> None:
        self._items[environment.id] = environment

    def get(self, environment_id: str) -> MusicEnvironment | None:
        return self._items.get(environment_id)

    def list(self, *, include_archived: bool = False) -> list[MusicEnvironment]:
        _ = include_archived
        return list(self._items.values())
