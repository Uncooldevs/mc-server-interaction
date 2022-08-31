import asyncio
import logging
import os
import shutil
import time
from typing import Dict, Tuple, Optional

import aiofile
import aiohttp

from mc_server_interaction.exceptions import ServerRunningException
from mc_server_interaction.interaction import MinecraftServer
from .data_store import ManagerDataStore
from .models import WorldGenerationSettings
from .utils import AvailableMinecraftServerVersions, copy_async
from ..interaction.models import ServerConfig, ServerStatus
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
            if not server.server_config.installed:
                server.set_status(ServerStatus.NOT_INSTALLED)
            self._servers[sid] = server

    async def start_server(self, sid):
        await self._servers.get(sid).start()

    async def stop_server(self, sid):
        await self._servers.get(sid).stop()

    async def stop_all_servers(self):
        await asyncio.gather(*[server.stop() for server in self._servers.values() if server.is_running])

    def get_servers(self) -> Dict[str, MinecraftServer]:
        """
        :return: Dictionary of sid: MinecraftServer
        """
        return self._servers

    def name_exists(self, name: str):
        return len(list(filter(lambda server: server.server_config.name == name, list(self._servers.values())))) != 0

    def delete_server(self, sid):
        """
        Deletes a server and all files
        :param sid: Sid of the server to delete
        :return:
        """
        server = self._servers.get(sid)
        if server.is_running:
            raise ServerRunningException()

        path = server.server_config.path
        shutil.rmtree(path)
        self._servers.pop(sid)
        self.config.remove_server(sid)
        self.config.save()

    async def create_new_server(self, name, version,
                                world_generation_settings: Optional[WorldGenerationSettings] = None) -> Tuple[
        str, MinecraftServer]:
        """
        Create necessary files like server.properties, eula.txt
        :param world_generation_settings: Settings for world generation
        :param name: Name of the server
        :param version: Minecraft version of the server. Accepts 'latest'
        :return: MinecraftServer
        """
        self.config.increment_sid()
        latest_sid = str(self.config.get_latest_sid())
        path = os.path.join(self.config.server_data_dir,
                            f'{"".join(c for c in name.replace(" ", "_") if c.isalnum()).strip()}_{latest_sid}'
                            )
        if version == "latest":
            version = self.available_versions.get_latest_version()

        config = ServerConfig(path=path, created_at=time.time(), version=version, name=name, installed=False)
        self.config.add_server(latest_sid, config)

        server = MinecraftServer(config)
        server.set_status(ServerStatus.NOT_INSTALLED)
        self._servers[latest_sid] = server
        self.config.save()
        if not os.path.exists(path):
            os.makedirs(path)

        # TODO interface for world generator settings
        if not world_generation_settings:
            world_generation_settings = WorldGenerationSettings()

        for name, value in world_generation_settings:
            server.properties.set(name, value)

        server.properties.set("level-name", "worlds/world")

        server.properties.save()

        self.logger.info("Write eula file")
        async with aiofile.async_open(os.path.join(path, "eula.txt"), "w") as f:
            await f.write("eula=true")

        server.set_status(ServerStatus.STOPPED)
        return latest_sid, server

    async def install_server(self, sid: str, force_redownload: bool = False):
        """

        Create server.jar in a blank created server

        :param force_redownload: Redownload server jar
        :param sid: sid of the server
        :return:
        """
        server = self._servers.get(sid)
        server.set_status(ServerStatus.INSTALLING)
        version = server.server_config.version
        path = server.server_config.path
        if os.path.exists(str(cache_dir / f"minecraft_server_{version}.jar")) and not force_redownload:
            self.logger.info(f"Using cached server jar for version {version}")
            await copy_async(str(cache_dir / f"minecraft_server_{version}.jar"), os.path.join(path, "server.jar"))

        else:
            self.logger.info(f"Downloading server jar for version {version}")
            download_url = await self.available_versions.get_download_link(version)
            async with aiohttp.ClientSession() as session:
                filename = str(cache_dir / f"minecraft_server_{version}.jar")
                async with aiofile.async_open(filename, "wb") as f:
                    resp = await session.get(download_url)
                    async for chunk in resp.content.iter_chunked(10 * 1024):
                        await f.write(chunk)

                await copy_async(filename, os.path.join(path, "server.jar"))

        server.set_status(ServerStatus.STOPPED)
        server.server_config.installed = True
        self.config.save()

    def get_server(self, sid) -> MinecraftServer:
        return self._servers.get(sid)
