import logging
import os.path


class LogNameFilter(logging.Filter):
    def filter(self, record):
        record.name_last = record.name.rsplit(".", 1)[-1]
        return True


def setup_logging():

    formatter = logging.Formatter("[%(asctime)s] [%(name_last)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")

    main_logger = logging.getLogger("MCServerInteraction")
    main_logger.setLevel(logging.DEBUG)

    if not os.path.exists("logs"):
        os.mkdir("logs")
    file_handler = logging.FileHandler("logs/MCServerInteraction.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(LogNameFilter())
    main_logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(LogNameFilter())
    main_logger.addHandler(console_handler)


