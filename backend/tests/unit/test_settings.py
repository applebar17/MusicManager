from pathlib import Path

from music_manager_backend.shared.settings import Settings, get_settings


def test_settings_defaults_are_local_first() -> None:
    settings = get_settings()

    assert settings.app_name == "Music Manager"
    assert settings.environment == "development"
    assert settings.data_dir == Path("local")
    assert settings.database_path == Path("local/music-manager.sqlite3")


def test_settings_accepts_overrides(tmp_path: Path) -> None:
    database_path = tmp_path / "test.sqlite3"

    settings = Settings(environment="test", database_path=database_path, log_level="DEBUG")

    assert settings.environment == "test"
    assert settings.database_path == database_path
    assert settings.log_level == "DEBUG"
