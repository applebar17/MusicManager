from pathlib import Path


class MetadataReader:
    def read(self, path: Path) -> dict[str, str | int | None]:
        return {"path": str(path), "title": None, "artist": None, "duration_seconds": None}

