import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Tuple, Optional

import aiofiles
import aiohttp

from mc_server_interaction.exceptions import ServerRunningException
from mc_server_interaction.interaction import MinecraftServer
from .backup_manager import BackupManager
from .data_store import ManagerDataStore
from .models import WorldGenerationSettings
from .utils import AvailableMinecraftServerVersions
from ..interaction.models import ServerConfig, ServerStatus
from ..paths import cache_dir
from ..utils.files import async_copy


class ServerManager:
    logger: logging.Logger
    available_versions = AvailableMinecraftServerVersions()
    _servers: Dict[str, MinecraftServer] = {}
    config: ManagerDataStore

    def __init__(self):
        self.logger = logging.getLogger(f"MCServerInteraction.{self.__class__.__name__}")
        self.config = ManagerDataStore()
        for sid, server_config in self.config.get_servers().items():
            server = MinecraftServer(server_config)
            self._servers[sid] = server

        self.backup_manager = BackupManager(self._servers)

    async def stop_all_servers(self):
        self.logger.info("Stopping all running servers")
        await asyncio.gather(
            *[server.shutdown() for server in self._servers.values() if server.is_running]
        )

    def get_servers(self) -> Dict[str, MinecraftServer]:
        """
        :return: Dictionary of sid: MinecraftServer
        """
        return self._servers

    def delete_server(self, sid):
        """
        Deletes a server and all files
        :param sid: Sid of the server to delete
        :return:
        """
        server = self._servers.get(sid)
        if server.is_running:
            raise ServerRunningException()

        self.logger.info(f"Deleting server {server.name}")
        path = server.server_config.path
        shutil.rmtree(path)
        self._servers.pop(sid)
        self.config.remove_server(sid)
        self.config.save()

    async def create_new_server(
            self,
            name,
            version,
            world_generation_settings: Optional[WorldGenerationSettings] = None
    ) -> Tuple[str, MinecraftServer]:
        """
        Create necessary files like server.properties, eula.txt
        :param world_path: Path to world directory
        :param world_generation_settings: Settings for world generation
        :param name: Name of the server
        :param version: Minecraft version of the server. Accepts 'latest'
        :return: MinecraftServer
        """
        self.config.increment_sid()
        latest_sid = str(self.config.get_latest_sid())
        path = os.path.join(
            self.config.server_data_dir,
            f'{"".join(c for c in name.replace(" ", "_") if c.isalnum()).strip()}_{latest_sid}',
        )
        if version == "latest":
            version = self.available_versions.get_latest_version()

        config = ServerConfig(
            path=path,
            created_at=time.time(),
            version=version,
            name=name,
            installed=False,
        )
        self.config.add_server(latest_sid, config)

        server = MinecraftServer(config)
        await server.set_status(ServerStatus.NOT_INSTALLED)
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
        server.properties.set("enable-query", True)

        server.properties.save()

        self.logger.info("Writing eula file")
        async with aiofiles.open(os.path.join(path, "eula.txt"), "w") as f:
            await f.write("eula=true")

        await server.set_status(ServerStatus.STOPPED)
        return latest_sid, server

    async def install_server(self, sid: str, force_redownload: bool = False):
        """
        Create server.jar in a blank created server
        :param force_redownload: Redownload server jar
        :param sid: sid of the server
        :return:
        """
        server = self._servers.get(sid)
        self.logger.info(f"Installing server {server.name}")
        await server.set_status(ServerStatus.INSTALLING)
        version = server.server_config.version
        path = server.server_config.path
        if (
                os.path.exists(str(cache_dir / f"minecraft_server_{version}.jar"))
                and not force_redownload
        ):
            self.logger.info(f"Using cached server jar for version {version}")
            await async_copy(
                (cache_dir / f"minecraft_server_{version}.jar"),
                Path(os.path.join(path, "server.jar")),
            )

        else:
            self.logger.info(f"Downloading server jar for version {version}")
            download_url = await self.available_versions.get_download_link(version)
            async with aiohttp.ClientSession() as session:
                filename = cache_dir / f"minecraft_server_{version}.jar"
                async with aiofiles.open(filename, "wb") as f:
                    resp = await session.get(download_url)
                    async for chunk in resp.content.iter_chunked(10 * 1024):
                        await f.write(chunk)

                await async_copy(filename, Path(os.path.join(path, "server.jar")))

        await server.set_status(ServerStatus.STOPPED)
        server.server_config.installed = True
        self.config.save()

    def get_server(self, sid) -> MinecraftServer:
        return self._servers.get(sid)
