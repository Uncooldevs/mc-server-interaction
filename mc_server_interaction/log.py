import logging
import logging.handlers
import os.path
from typing import Union

from mc_server_interaction.paths import data_dir

logger = logging.getLogger("MCServerInteraction")


class LogNameFilter(logging.Filter):
    def filter(self, record):
        record.name_last = record.name.rsplit(".", 1)[-1]
        return True


def setup_logging():
    log_path = str(data_dir / "logs")
    formatter = logging.Formatter(
        "[%(asctime)s] [%(name_last)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    main_logger = logging.getLogger("MCServerInteraction")
    main_logger.setLevel(logging.DEBUG)

    if not os.path.exists(log_path):
        os.mkdir(log_path)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        f"{log_path}/MCServerInteraction.log", when="midnight"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(LogNameFilter())
    main_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(LogNameFilter())
    main_logger.addHandler(console_handler)


def set_console_log_level(level: Union[str, int]):
    for handler in logger.handlers:
        if type(handler) == logging.StreamHandler:
            handler.setLevel(level)
            break
