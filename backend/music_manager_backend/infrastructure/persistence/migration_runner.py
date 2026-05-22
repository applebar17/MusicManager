from pathlib import Path

from alembic import command
from alembic.config import Config


def alembic_config(database_path: Path) -> Config:
    config_path = Path(__file__).resolve().parents[4] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    return config


def upgrade_database(database_path: Path) -> None:
    if database_path != Path(":memory:"):
        database_path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(database_path), "head")
