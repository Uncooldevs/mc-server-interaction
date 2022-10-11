import logging
import os
from typing import Optional


class ServerProperties:
    logger: logging.Logger
    __data: dict

    def __init__(self, file_name: str, server_name: str):
        self.logger = logging.getLogger(
            f"MCServerInteraction.{self.__class__.__name__}:{server_name}"
        )
        self.file_name = file_name
        self.__data = {}
        if not os.path.exists(file_name):
            self.logger.warning("Properties file not found, creating empty instance")
            return
        with open(file_name, "r", encoding="utf-8") as f:
            for i in f:
                if i.startswith("#"):
                    continue

                key, raw_value = i.split("=")
                raw_value = raw_value.rstrip("\n")

                if raw_value in ["true", "false"]:
                    value = raw_value == "true"
                else:
                    try:
                        value = int(raw_value)
                    except ValueError:
                        value = raw_value

                self.__data[key] = value
            self.logger.debug(f"Loaded {len(self.__data)} entries from properties file")

    def set(self, key, value):
        self.__data[key] = value

    def get(self, key, fallback=None):
        return self.__data.get(key, fallback)

    def __str__(self):
        return str(self.__data)

    def to_dict(self):
        return self.__data

    def save(self, override_filename: Optional[str] = None):
        with open(override_filename or self.file_name, "w", encoding="utf-8") as f:
            for key, raw_value in self.__data.items():
                if type(raw_value) == bool:
                    value = str(raw_value).lower()
                elif raw_value is None:
                    value = ""
                else:
                    value = str(raw_value)
                f.write(f"{key}={value}\n")
        self.logger.debug(f"Saved {len(self.__data)} server properties")
