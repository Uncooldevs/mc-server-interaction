import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, Union

from cached_property import cached_property_with_ttl
from mcstatus import JavaServer

from mc_server_interaction.exceptions import ServerRunningException, ServerNotInstalledException
from mc_server_interaction.interaction.models import ServerStatus, Player, ServerConfig, BannedPlayer, \
    OPPlayer
from mc_server_interaction.interaction.property_handler import ServerProperties
from mc_server_interaction.interaction.server_process import ServerProcess


class MinecraftServer:
    logger: logging.Logger
    process: Optional[ServerProcess]
    server_config: ServerConfig
    _status: ServerStatus
    properties: ServerProperties
    _mcstatus_server: Optional[JavaServer]

    def __init__(self, server_config: ServerConfig):
        self.logger = logging.getLogger(f"MCServerInteraction.{self.__class__.__name__}:{server_config.name}")
        self.server_config = server_config

        self._status = ServerStatus.STOPPED
        self.process = None
        self._mcstatus_server = None

        self.load_properties()

    def load_properties(self):
        properties_file = os.path.join(self.server_config.path, "server.properties")
        self.logger.debug(f"Attempting to load server properties from {properties_file}")
        self.properties = ServerProperties(properties_file)

    def save_properties(self):
        self.logger.debug("Saving server properties")
        self.properties.save()

    def get_properties(self) -> ServerProperties:
        return self.properties

    def set_property(self, key: str, value: Union[str, int, float, bool]):
        self.properties.set(key, value)

    def set_status(self, status: ServerStatus):
        self.logger.debug(f"Setting server status to {status}")
        self._status = status

    async def start(self):
        if self.is_running:
            raise ServerRunningException()
        if self._status == ServerStatus.NOT_INSTALLED or self._status == ServerStatus.INSTALLING:
            raise ServerNotInstalledException()
        jar_path = os.path.join(self.server_config.path, "server.jar")
        if not os.path.exists(jar_path):
            raise FileNotFoundError()
        self.logger.info("Starting server")
        self.properties.save()
        command = ["java", f"-Xmx{self.server_config.ram}M", f"-Xms{self.server_config.ram}M", "-jar",
                   jar_path, "--nogui"]
        self.process = ServerProcess()
        await self.process.start(command, self.server_config.path)
        self.logger.debug("Create asyncio task for stdout callback")
        asyncio.create_task(self.process.read_output())

        self.process.callbacks.stdout.add_callback(self._update_status_callback)
        self.set_status(ServerStatus.STARTING)

    async def stop(self, timeout=60):
        if self.is_online:
            self.logger.info("Stopping server")
            await self.process.send_input("stop")
            self.set_status(ServerStatus.STOPPING)
            for i in range(timeout):
                await asyncio.sleep(1)
                if not self.is_online:
                    return
            # kill if timeout expired
            self.logger.error("Timeout expired, killing server")
            self.kill()

        else:
            self.logger.warning("Server not running")

    def kill(self):
        if self.is_running:
            self.logger.info("Killing server process")
            self.process.kill()
            self.set_status(ServerStatus.STOPPED)

    def get_status(self) -> ServerStatus:
        return self._status

    @cached_property_with_ttl(ttl=5)
    def system_load(self):
        if self.is_running:
            return self.process.get_resource_usage()

    @cached_property_with_ttl(ttl=30)
    def banned_players(self):
        banned_players = []
        banned_players_file = os.path.join(self.server_config.path, "banned-players.json")
        if os.path.isfile(banned_players_file):
            self.logger.debug(f"Loading banned players from {banned_players_file}")
            with open(banned_players_file, "r") as f:
                data = json.load(f)
            for player_data in data:
                name = player_data["name"]
                timestamp = datetime.strptime(player_data["created"].split(" +")[0], "%Y-%m-%d %H:%M:%S").timestamp()
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
    def players(self):
        players = []
        banned_players = self.banned_players
        op_players = self.op_players
        op_players = list(
            filter(lambda player: not any(banned_player.name == player.name for banned_player in banned_players),
                   op_players))
        other_players = banned_players + op_players

        online_player_names = []
        if self._mcstatus_server is not None:
            self.logger.info("Retrieving online players via query port")
            online_player_names = self._mcstatus_server.query().players.names
        for name in online_player_names:
            existing_player = next((player for player in other_players if player.name == name), None)
            if existing_player is not None:
                other_players.remove(existing_player)
                existing_player.is_online = True
                players.append(existing_player)
            else:
                players.append(Player(name, is_online=True))
        players += other_players
        return players

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

    async def _send_command(self, command):
        self.logger.info(f"Sending command {command} to server")
        await self.process.send_input(command)

    def _update_status_callback(self, output: str):
        if self._status == ServerStatus.STARTING:
            if "For help, type \"help\"" in output:
                if self.properties.get("enable-query"):
                    self._mcstatus_server = JavaServer("localhost", self.properties.get("server-port"))
                self.set_status(ServerStatus.RUNNING)
        if "[Server thread/INFO]: Stopping the server" in output:
            self.set_status(ServerStatus.STOPPING)
        if "[Server thread/INFO]: ThreadedAnvilChunkStorage: All dimensions are saved" in output:
            self._mcstatus_server = None
            self.process = None
            self.set_status(ServerStatus.STOPPED)
