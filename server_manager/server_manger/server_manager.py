import logging
import os
import shutil
import time
from typing import Dict

import requests

from server_manager.exceptions import DirectoryNotEmptyException, ServerRunningException
from server_manager.mc_server_interaction import MinecraftServer
from .data_store import ManagerDataStore
from .models import WorldGenerationSettings
from .utils import AvailableMinecraftServerVersions
from ..mc_server_interaction.models import ServerConfig
from ..paths import cache_dir


class ServerManager:
    logger: logging.Logger
    available_versions = AvailableMinecraftServerVersions()
    _servers: Dict[str, MinecraftServer] = {}
    config: ManagerDataStore

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = ManagerDataStore()
        for sid, server_config in self.config.get_servers().items():
            server = MinecraftServer(server_config)
            self._servers[sid] = server

    def start_server(self, sid):
        self._servers.get(sid).start()

    def stop_server(self, sid):
        self._servers.get(sid).stop()

    def stop_all_servers(self):
        for server in self._servers.values():
            server.stop()

    def get_servers(self):
        return self._servers

    def delete_server(self, sid):
        server = self._servers.get(sid)
        if server.is_running:
            raise ServerRunningException()

        path = server.server_config.path
        shutil.rmtree(path)
        self._servers.pop(sid)
        self.config.remove_server(sid)
        self.config.save()

    def create_new_server(self, name, version):
        path = os.path.join(self.config.server_data_dir, "".join(c for c in name.replace(" ", "_") if c.isalnum()).strip())
        if not os.path.exists(path):
            os.makedirs(path)
        if len(os.listdir(path)) > 0:
            raise DirectoryNotEmptyException(f"Directory {path} is not empty")
        if os.path.exists(f"cache/minecraft_server_{version}.jar"):
            self.logger.info(f"Using cached server jar for version {version}")
            shutil.copy(f"cache/minecraft_server_{version}.jar", os.path.join(path, "server.jar"))

        else:
            self.logger.info(f"Downloading server jar for version {version}")
            download_url = self.available_versions.get_download_link(version)
            resp = requests.get(download_url)
            if resp.status_code == 200:
                filename = str(cache_dir / f"minecraft_server_{version}.jar")
                with open(filename, "wb") as f:
                    f.write(resp.content)
                shutil.copy(filename, os.path.join(path, "server.jar"))
            else:
                raise Exception(f"Error downloading server jar for version {version}")

        self.config.increment_sid()
        config = ServerConfig(path=path, created_at=time.time(), version=version, name=name)
        self.config.add_server(self.config.get_latest_sid(), config)
        server = MinecraftServer(config)
        self._servers[str(self.config.get_latest_sid())] = server

        # TODO interface for world generator settings
        world_generator_settings = WorldGenerationSettings()

        for name, value in world_generator_settings:
            server.properties.set(name, value)

        server.properties.save()

        self.logger.info("Write eula file")
        with open(os.path.join(path, "eula.txt"), "w") as f:
            f.write("eula=true")

    def get_server(self, sid) -> MinecraftServer:
        return self._servers.get(sid)
