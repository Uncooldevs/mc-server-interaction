import json
import os
from logging import getLogger
from typing import Dict

from server_manager.mc_server_interaction import ServerConfig

logger = getLogger("DataStore")


class ManagerDataStore:

    _servers: Dict[str, ServerConfig]
    data_file = "manager_data.json"
    _latest_sid: int = 0

    def __init__(self):
        self._servers = {}
        self.load_data()

    def get_servers(self):
        return self._servers

    def increment_sid(self):
        self._latest_sid += 1
        self.save()

    def get_latest_sid(self):
        return self._latest_sid

    def add_server(self, sid, server_config: ServerConfig):
        self._servers[sid] = server_config
        self.save()

    def load_data(self):
        if not os.path.exists(self.data_file):
            self._servers = {}
            self._latest_sid = 0
            return
        with open(self.data_file, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error loading data: {e}")
                return

            self._latest_sid = data.get("latest_sid", 0)

            for sid, config in data["servers"]:
                try:
                    self._servers[sid] = ServerConfig(**config)
                except Exception as e:
                    logger.error(f"Error loading server config for {sid}: {e}")

    def save(self):
        with open(self.data_file, "w") as f:
            json.dump({
                "servers": {sid: config.__dict__ for sid, config in self._servers.items()},
            }, f, indent=4)
