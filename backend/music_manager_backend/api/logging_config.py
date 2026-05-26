import logging
from logging.handlers import RotatingFileHandler

from music_manager_backend.shared.settings import Settings

HANDLER_MARKER = "_music_manager_backend_handler"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
MAX_LOG_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def configure_logging(settings: Settings) -> None:
    log_path = settings.log_file_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(LOG_FORMAT)
    console = logging.StreamHandler()
    console.setLevel(settings.log_console_level)
    console.setFormatter(formatter)
    setattr(console, HANDLER_MARKER, True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(settings.log_file_level)
    file_handler.setFormatter(formatter)
    setattr(file_handler, HANDLER_MARKER, True)

    root.addHandler(console)
    root.addHandler(file_handler)
    package_logger = logging.getLogger("music_manager_backend")
    package_logger.disabled = False
    package_logger.setLevel(logging.DEBUG)
    for name, logger in logging.root.manager.loggerDict.items():
        if name.startswith("music_manager_backend") and isinstance(logger, logging.Logger):
            logger.disabled = False
