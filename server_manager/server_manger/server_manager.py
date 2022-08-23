import os
import shutil
import subprocess
import time
from logging import getLogger
from typing import Dict

import requests

from .utils import AvailableMinecraftServerVersions
from .data_store import ManagerDataStore
from server_manager.mc_server_interaction import MinecraftServer, ServerConfig
from server_manager.mc_server_interaction.exceptions import DirectoryNotEmptyException

logger = getLogger("ServerManager")


class ServerManager:
    available_versions = AvailableMinecraftServerVersions()
    _servers: Dict[str, MinecraftServer] = {}
    config: ManagerDataStore

    def __init__(self):
        self.config = ManagerDataStore()
        for sid, server_config in self.config.get_servers().items():
            server = MinecraftServer(server_config)
            self._servers[sid] = server

    def start_server(self, sid):
        self._servers.get(sid).start()

    def stop_server(self, sid):
        self._servers.get(sid).start()

    def get_servers(self):
        return self._servers

    def create_new_server(self, name, path, version):
        if not os.path.exists(path):
            os.makedirs(path)
        if len(os.listdir(path)) > 0:
            raise DirectoryNotEmptyException(f"Directory {path} is not empty")
        if os.path.exists(f"cache/minecraft_server_{version}.jar"):
            logger.info("Using cached jar file")
            shutil.copy(f"cache/minecraft_server_{version}.jar", os.path.join(path, "server.jar"))

        else:
            logger.info("Downloading jar file")
            download_url = self.available_versions.get_download_link(version)
            resp = requests.get(download_url)
            if resp.status_code == 200:
                if not os.path.exists("cache/"):
                    os.mkdir("cache/")
                with open(f"cache/minecraft_server_{version}.jar", "wb") as f:
                    f.write(resp.content)
                shutil.copy(f"cache/minecraft_server_{version}.jar", os.path.join(path, "server.jar"))

        subprocess.call("java -jar server.jar --nogui".split(), cwd=path)

        self.config.increment_sid()
        config = ServerConfig(path=path, created_at=time.time(), version=version, name=name)
        self.config.add_server(self.config.get_latest_sid(), config)
        self._servers[self.config.get_latest_sid()] = MinecraftServer(
            config
        )

    def get_server(self, sid) -> MinecraftServer:
        return self._servers.get(sid)
