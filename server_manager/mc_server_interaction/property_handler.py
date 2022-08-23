import os
from typing import Optional


class ServerProperties:
    __data: dict

    def __init__(self, file_name: str):
        self.file_name = file_name
        self.__data = {}
        if not os.path.exists(file_name):
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

    def set(self, key, value):
        self.__data[key] = value

    def get(self, key, fallback=None):
        return self.__data.get(key, fallback)

    def __str__(self):
        return str(self.__data)

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


