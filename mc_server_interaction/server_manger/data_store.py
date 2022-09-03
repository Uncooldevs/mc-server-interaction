import json
import logging
import os
from typing import Dict

from mc_server_interaction.interaction.models import ServerConfig
from mc_server_interaction.paths import data_dir


class ManagerDataStore:
    logger: logging.Logger
    _servers: Dict[str, ServerConfig]
    data_file = str(data_dir / "manager_data.json")
    _latest_sid: int = 0
    server_data_dir = str(data_dir / "servers")

    def __init__(self):
        self.logger = logging.getLogger(
            f"MCServerInteraction.{self.__class__.__name__}"
        )
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

    def remove_server(self, sid):
        self._servers.pop(sid)

    def load_data(self):
        if not os.path.exists(self.data_file):
            self._servers = {}
            self._latest_sid = 0
            return
        with open(self.data_file, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"Error loading data: {e}")
                return

            self._latest_sid = data.get("latest_sid", 0)
            self.server_data_dir = data.get("server_data_dir", self.server_data_dir)

            for sid, config in data.get("servers", {}).items():
                try:
                    self._servers[sid] = ServerConfig(**config)
                except Exception as e:
                    self.logger.error(f"Error loading server config for {sid}: {e}")

    def save(self):
        with open(self.data_file, "w") as f:
            json.dump(
                {
                    "servers": {
                        sid: config.__dict__ for sid, config in self._servers.items()
                    },
                    "latest_sid": self._latest_sid,
                    "server_data_dir": self.server_data_dir,
                },
                f,
                indent=4,
            )
