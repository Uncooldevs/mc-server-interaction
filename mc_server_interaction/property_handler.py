class ServerProperties:
    __data: dict

    def __init__(self, file_name: str):
        self.__data = {}
        with open(file_name, "r") as f:
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

    def get(self, key, fallback):
        return self.__data.get(key, fallback)

    def __str__(self):
        return str(self.__data)
