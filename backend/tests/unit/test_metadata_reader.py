import json
from pathlib import Path
from typing import Any

from tinytag import TinyTagException

from music_manager_backend.infrastructure.audio import MetadataReader


class FakeTag:
    title = " Track "
    artist = "Artist"
    album = "Album"
    duration = 199.6
    bpm = "124"
    key = "8A"
    comment = "Warmup"

    def as_dict(self) -> dict[str, object]:
        return {"title": self.title, "duration": self.duration, "nested": object()}


def test_metadata_reader_normalizes_tinytag_values(tmp_path: Path) -> None:
    path = tmp_path / "track.mp3"
    path.write_bytes(b"fake")
    reader = MetadataReader(tag_factory=lambda _path: FakeTag())

    metadata = reader.read(path)

    assert metadata.title == "Track"
    assert metadata.artist == "Artist"
    assert metadata.album == "Album"
    assert metadata.duration_seconds == 200
    assert metadata.bpm == 124
    assert metadata.key == "8A"
    assert metadata.comment == "Warmup"
    json.dumps(metadata.raw)


def test_metadata_reader_returns_warning_for_unreadable_file(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.mp3"
    path.write_bytes(b"not audio")

    def fail(_path: str) -> Any:
        raise TinyTagException("could not read")

    metadata = MetadataReader(tag_factory=fail).read(path)

    assert metadata.title is None
    assert metadata.raw == {}
    assert metadata.warnings == ("metadata_unreadable: could not read",)
