import logging
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = "/var/log/app"

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_console_handler: logging.StreamHandler | None = None
_file_handler: RotatingFileHandler | None = None


class _SqlalchemyFilter(logging.Filter):
    def __init__(self, exclude: bool = False) -> None:
        super().__init__()
        self.exclude = exclude

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        return not (self.exclude and record.name.startswith("sqlalchemy"))


def setup_logging(
    app_name: str,
    default_level: str = "INFO",
    module_levels: dict[str, str] | None = None,
) -> None:
    global _console_handler, _file_handler

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    _console_handler = logging.StreamHandler(sys.stdout)
    _console_handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(_console_handler)

    _file_handler = RotatingFileHandler(
        f"{LOG_DIR}/{app_name}.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    _file_handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(_file_handler)

    log_levels = logging.getLevelNamesMapping()
    root.setLevel(log_levels.get(default_level.upper(), logging.INFO))

    if module_levels:
        for name, level in module_levels.items():
            logging.getLogger(name).setLevel(log_levels.get(level.upper(), logging.INFO))


def setup_sqlalchemy_logging(
    log_level: str = "WARNING",
    log_output: str = "both",
) -> None:
    engine_logger = logging.getLogger("sqlalchemy.engine")
    log_levels = logging.getLevelNamesMapping()
    engine_logger.setLevel(log_levels.get(log_level.upper(), logging.INFO))

    for handler in (_console_handler, _file_handler):
        if handler is None:
            continue
        handler.filters = [
            f for f in handler.filters
            if not isinstance(f, _SqlalchemyFilter)
        ]

    if log_output == "console" and _file_handler:
        _file_handler.addFilter(_SqlalchemyFilter(exclude=True))
    elif log_output == "file" and _console_handler:
        _console_handler.addFilter(_SqlalchemyFilter(exclude=True))
