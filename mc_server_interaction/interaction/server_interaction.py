import asyncio
import dataclasses
import json
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List

from cached_property import cached_property_with_ttl
from mcstatus import JavaServer

from mc_server_interaction.exceptions import (
    ServerRunningException,
    ServerNotInstalledException, NotAWorldFolderException, WorldExistsException,
)
from mc_server_interaction.interaction.models import (
    ServerStatus,
    Player,
    ServerConfig,
    BannedPlayer,
    OPPlayer,
)
from mc_server_interaction.interaction.property_handler import ServerProperties
from mc_server_interaction.interaction.server_process import ServerProcess, Callback
from mc_server_interaction.interaction.worlds import MinecraftWorld
from mc_server_interaction.manager.models import WorldGenerationSettings


class ServerCallbacks:

    def __init__(self):
        self.output = Callback()
        self.status = Callback()
        self.properties = Callback()
        self.system_metrics = Callback()
        self.players = Callback()


class MinecraftServer:
    logger: logging.Logger

    server_config: ServerConfig
    _status: ServerStatus
    properties: ServerProperties
    _mcstatus_server: Optional[JavaServer]
    log: deque
    callbacks: ServerCallbacks
    worlds: List[MinecraftWorld]
    active_world: MinecraftWorld

    def __init__(self, server_config: ServerConfig):
        self.logger = logging.getLogger(
            f"MCServerInteraction.{self.__class__.__name__}:{server_config.name.replace('.', '_')}"
        )
        self.server_config = server_config
        if self.server_config.installed:
            self._status = ServerStatus.STOPPED
        else:
            self._status = ServerStatus.NOT_INSTALLED
        self.process: Optional[ServerProcess] = None
        self._mcstatus_server = None
        self.log = deque(maxlen=128)
        self.callbacks = ServerCallbacks()

        self.load_properties()
        self.load_worlds()

        self.callbacks.status.add_callback(self._reload_worlds)
        asyncio.create_task(self._update_loop())

    def load_properties(self):
        properties_file = os.path.join(self.server_config.path, "server.properties")
        self.logger.debug(
            f"Attempting to load server properties from {properties_file}"
        )
        self.properties = ServerProperties(properties_file, self.name)

    def save_properties(self):
        self.logger.debug("Saving server properties")
        self.properties.save()

    def load_worlds(self):
        world_path = Path(self.server_config.path) / "worlds"
        self.logger.debug(f"Loading worlds from folder {str(world_path)}")
        self.worlds = []
        if not world_path.is_dir():
            return
        for entry in world_path.iterdir():
            if entry.is_dir():
                try:
                    world = MinecraftWorld(entry, server_name=self.name)
                    self.worlds.append(world)
                except NotAWorldFolderException:
                    self.logger.warning(f"Directory {entry.name} is not a Minecraft world")
        self.logger.debug(f"Loaded {len(self.worlds)} worlds from {str(world_path)}")
        self.active_world = self.get_world(self.properties.get("level-name").replace("worlds/", ""))

    def get_properties(self) -> ServerProperties:
        return self.properties

    def set_property(self, key: str, value: Union[str, int, float, bool]):
        self.properties.set(key, value)

    async def set_status(self, status: ServerStatus):
        if self._status != status:
            self.logger.debug(f"Setting server status to {status}")
            self._status = status
            await self.callbacks.status(status)

    async def set_active_world(self, world_name: str, new: bool = False):
        """
        Set the world for the server. Restarts the server if it is running.
        :param world_name: The name of the world
        :param new: If set to True, will not check if world exits, because it does not exist yet
        :return:
        """
        self.logger.debug(f"Setting world to {world_name}...")
        world = self.get_world(world_name)
        if world is None and not new:
            self.logger.error("A world with this name does not exist")
            raise NotAWorldFolderException()
        if self.is_running:
            self.logger.debug("Restarting server to change world...")
            await self.shutdown()
            self.logger.debug(f"Changing world to {world_name}")
            self.set_property("level-name", f"worlds/{world_name}")
            self.active_world = world
            await self.start()
        else:
            self.set_property("level-name", f"worlds/{world_name}")
            self.active_world = world

    async def create_new_world(self, world_name: str, world_generation_settings: WorldGenerationSettings):
        """
        Create a new world. This function does not actually creates a new world but sets all properties so that
        the server can generate the world on next startup.
        :param world_name: The name of the new world
        :param world_generation_settings: The properties for world generation
        :return:
        """
        self.logger.debug(f"Setting up new world {world_name}")
        if not world_generation_settings:
            world_generation_settings = WorldGenerationSettings()

        if self.world_exits(world_name):
            self.logger.error("A world with this name does already exist")
            raise WorldExistsException()
        for name, value in world_generation_settings:
            self.properties.set(name, value)

    async def start(self):
        if self.is_running:
            raise ServerRunningException()
        if (
                self._status == ServerStatus.NOT_INSTALLED
                or self._status == ServerStatus.INSTALLING
        ):
            raise ServerNotInstalledException()
        jar_path = os.path.join(self.server_config.path, "server.jar")
        if not os.path.exists(jar_path):
            raise FileNotFoundError()
        self.logger.info("Starting server")
        self.save_properties()
        command = [
            "java",
            f"-Xmx{self.server_config.ram}M",
            f"-Xms{self.server_config.ram}M",
            "-jar",
            jar_path,
            "--nogui",
        ]
        self.process = ServerProcess(self.name)
        await self.process.start(command, self.server_config.path)
        self.logger.debug("Create asyncio task for stdout callback")
        asyncio.create_task(self.process.read_output())

        self.process.callbacks.stdout.add_callback(self._update_status_callback)
        await self.set_status(ServerStatus.STARTING)

    @property
    def name(self):
        return self.server_config.name

    async def stop(self):
        """
        Tells the server to stop and returns, there is no guarantee the server will actually stop.
        """
        if self.is_online:
            self.logger.info("Stopping server")
            await self.process.send_input("stop")
            await self.set_status(ServerStatus.STOPPING)
        else:
            self.logger.warning("Server not running")

    async def shutdown(self, timeout=120):
        """
        Same as stop, but waits for the server to shut down or kills the process
        if the server does not shut down on its own.
        :param timeout: The maximum time to wait in seconds before the server process will be killed.
        """
        if self.is_online:
            await self.stop()
            for i in range(timeout):
                await asyncio.sleep(1)
                if not self.is_running:
                    return
            # kill if timeout expired
            self.logger.error("Timeout expired, killing server")
            self.kill()
            await asyncio.sleep(1)
            await self.set_status(ServerStatus.STOPPED)
            self.save_properties()
        else:
            self.logger.warning("Server not running")

    def kill(self):
        if self.is_running:
            self.logger.info("Killing server process")
            self.process.kill()

    @property
    def status(self) -> ServerStatus:
        return self._status

    @cached_property_with_ttl(ttl=5)
    def system_load(self) -> dict:
        if self.is_running:
            return self.process.get_resource_usage()
        return {
            "cpu": {"percent": 0},
            "memory": {"total": 0, "used": 0, "server": 0},
        }

    @cached_property_with_ttl(ttl=30)
    def banned_players(self):
        banned_players = []
        banned_players_file = os.path.join(
            self.server_config.path, "banned-players.json"
        )
        if os.path.isfile(banned_players_file):
            self.logger.debug(f"Loading banned players from {banned_players_file}")
            with open(banned_players_file, "r") as f:
                data = json.load(f)
            for player_data in data:
                name = player_data["name"]
                timestamp = datetime.strptime(
                    player_data["created"].split(" +")[0], "%Y-%m-%d %H:%M:%S"
                ).timestamp()
                player = BannedPlayer(name)
                player.is_banned = True
                player.banned_since = timestamp
                player.ban_reason = player_data["reason"]
                banned_players.append(player)
        return banned_players

    @cached_property_with_ttl(ttl=30)
    def op_players(self):
        op_players = []
        op_players_file = os.path.join(self.server_config.path, "ops.json")
        if os.path.isfile(op_players_file):
            self.logger.debug(f"Loading op players from {op_players_file}")
            with open(op_players_file, "r") as f:
                data = json.load(f)
            for player_data in data:
                name = player_data["name"]
                player = OPPlayer(name)
                player.is_op = True
                player.op_level = player_data["level"]
                op_players.append(player)
        return op_players

    @cached_property_with_ttl(ttl=10)
    def online_players(self):
        online_players = []
        if self._mcstatus_server is not None:
            online_players = self._mcstatus_server.query().players.names
        online_players = [Player(name=name, is_online=True) for name in online_players]
        return online_players

    @cached_property_with_ttl(ttl=30)
    def whitelisted_players(self):
        whitelisted_players = []
        whitelist_file = os.path.join(self.server_config.path, "whitelist.json")
        if os.path.isfile(whitelist_file):
            self.logger.debug(f"Loading whitelisted players from {whitelist_file}")
            with open(whitelist_file, "r") as f:
                data = json.load(f)
            for player_data in data:
                name = player_data["name"]
                player = Player(name)
                whitelisted_players.append(player)
        return whitelisted_players

    @cached_property_with_ttl(ttl=10)
    def players(self):
        players = []
        banned_players = self.banned_players
        op_players = self.op_players
        op_players = list(
            filter(
                lambda player: not any(
                    banned_player.name == player.name
                    for banned_player in banned_players
                ),
                op_players,
            )
        )  # players can be op and banned for some reason, so filter ops

        online_players = self.online_players
        for player in online_players:
            op_player = next((p for p in op_players if p.name == player.name), None)
            if op_player is not None:
                op_player.is_online = True
                player.is_op = True
            players.append(player)

        players_dict = {
            "online_players": players,
            "op_players": op_players,
            "banned_players": banned_players,
        }
        return players_dict

    def get_world(self, name: str):
        if len(self.worlds) > 0:
            return next((world for world in self.worlds if world.name == name), None)
        return None

    def world_exits(self, name: str):
        return self.get_world(name) is not None

    async def send_command(self, command: str):
        if self.is_online:
            if command.startswith("/"):
                command = command.lstrip("/")

            await self._send_command(command)

        else:
            self.logger.warning("Server not running")

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.is_running()

    @property
    def is_online(self) -> bool:
        return self.is_running and self._status == ServerStatus.RUNNING

    @property
    def logs(self):
        return "\n".join(self.log) + ("\n" if self.log else "")

    async def _send_command(self, command):
        self.logger.info(f"Sending command {command} to server")
        await self.process.send_input(command)

    async def _update_status_callback(self, output: str):
        self.log.append(output)
        await self.callbacks.output(output)
        if self._status == ServerStatus.STARTING:
            if 'For help, type "help"' in output:
                if self.properties.get("enable-query"):
                    self._mcstatus_server = JavaServer(
                        "localhost", self.properties.get("server-port")
                    )
                await self.set_status(ServerStatus.RUNNING)
        if "[Server thread/INFO]: Stopping the server" in output:
            await self.set_status(ServerStatus.STOPPING)
        if (
                "[Server thread/INFO]: ThreadedAnvilChunkStorage: All dimensions are saved"
                in output
        ):
            self._mcstatus_server = None
            self.process = None
            await self.set_status(ServerStatus.STOPPED)
            self.save_properties()

    async def _update_loop(self):
        callbacks = {
            "players": self.callbacks.players,
            "system_metrics": self.callbacks.system_metrics
        }
        old_variables = {
            "system_metrics": None,
            "players": None
        }
        while True:
            if self._status not in [ServerStatus.STOPPED, ServerStatus.NOT_INSTALLED, ServerStatus.INSTALLING]:
                if not self.is_running:
                    self.process = None
                    await self.set_status(ServerStatus.STOPPED)

            for callback_name in callbacks.keys():
                callback = callbacks[callback_name]
                value = None
                if len(callback) > 0:
                    if callback_name == "players":
                        players = self.players
                        players = {
                            "online_players": [dataclasses.asdict(player) for player in players["online_players"]],
                            "op_players": [dataclasses.asdict(player) for player in players["op_players"]],
                            "banned_players": [dataclasses.asdict(player) for player in players["banned_players"]]
                        }
                        value = players
                    elif callback_name == "system_metrics":
                        value = self.system_load
                if value != old_variables[callback_name]:
                    await callback(value)
                    old_variables[callback_name] = value

            await asyncio.sleep(1)

    async def _reload_worlds(self, status: ServerStatus):
        if status == ServerStatus.RUNNING:
            self.load_worlds()
