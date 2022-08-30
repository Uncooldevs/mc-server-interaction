import asyncio
import logging
import os
import shutil
import time
from typing import Dict

import aiofile
import aiohttp

from mc_server_interaction.exceptions import DirectoryNotEmptyException, ServerRunningException
from mc_server_interaction.mc_server_interaction import MinecraftServer
from .data_store import ManagerDataStore
from .models import WorldGenerationSettings
from .utils import AvailableMinecraftServerVersions, copy_async
from ..mc_server_interaction.models import ServerConfig, ServerStatus
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

    async def start_server(self, sid):
        await self._servers.get(sid).start()

    async def stop_server(self, sid):
        await self._servers.get(sid).stop()

    async def stop_all_servers(self):
        await asyncio.gather(*[server.stop() for server in self._servers.values() if server.is_running])

    def get_servers(self):
        return self._servers

    def name_exists(self, name: str):
        return len(list(filter(lambda server: server.server_config.name == name, list(self._servers.values())))) != 0

    def delete_server(self, sid):
        server = self._servers.get(sid)
        if server.is_running:
            raise ServerRunningException()

        path = server.server_config.path
        shutil.rmtree(path)
        self._servers.pop(sid)
        self.config.remove_server(sid)
        self.config.save()

    async def create_new_server(self, name, version):

        path = os.path.join(self.config.server_data_dir,
                            "".join(c for c in name.replace(" ", "_") if c.isalnum()).strip())
        if not os.path.exists(path):
            os.makedirs(path)
        if version == "latest":
            version = self.available_versions.get_latest_version()

        if len(os.listdir(path)) > 0:
            raise DirectoryNotEmptyException(f"Directory {path} is not empty")
        if os.path.exists(str(cache_dir / f"minecraft_server_{version}.jar")):
            self.logger.info(f"Using cached server jar for version {version}")
            await copy_async(str(cache_dir / f"minecraft_server_{version}.jar"), os.path.join(path, "server.jar"))

        else:
            self.logger.info(f"Downloading server jar for version {version}")
            download_url = await self.available_versions.get_download_link(version)
            async with aiohttp.ClientSession() as session:
                resp = await session.get(download_url)

            if resp.status == 200:
                filename = str(cache_dir / f"minecraft_server_{version}.jar")
                with aiofile.async_open(filename, "wb") as f:
                    f.write(resp.content)
                await copy_async(filename, os.path.join(path, "server.jar"))
            else:
                raise Exception(f"Error downloading server jar for version {version}")

        self.config.increment_sid()
        config = ServerConfig(path=path, created_at=time.time(), version=version, name=name)
        self.config.add_server(self.config.get_latest_sid(), config)
        server = MinecraftServer(config)
        server.set_status(ServerStatus.INSTALLING)
        self._servers[str(self.config.get_latest_sid())] = server

        # TODO interface for world generator settings
        world_generator_settings = WorldGenerationSettings()

        for name, value in world_generator_settings:
            server.properties.set(name, value)

        server.properties.save()

        self.logger.info("Write eula file")
        async with aiofile.async_open(os.path.join(path, "eula.txt"), "w") as f:
            await f.write("eula=true")

    def get_server(self, sid) -> MinecraftServer:
        return self._servers.get(sid)