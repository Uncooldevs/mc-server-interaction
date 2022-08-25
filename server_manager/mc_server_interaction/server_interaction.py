import json
import logging
import os
import subprocess
from threading import Thread
from typing import Optional, Union
from datetime import datetime

from mcstatus import JavaServer
from cached_property import cached_property_with_ttl

from server_manager.mc_server_interaction.exceptions import ServerAlreadyRunningException, ServerNotInstalledException
from server_manager.mc_server_interaction.models import ServerStatus, Player, ServerConfig, BannedPlayer, OPPlayer
from server_manager.mc_server_interaction.server_process import ServerProcess
from server_manager.mc_server_interaction.property_handler import ServerProperties


class MinecraftServer:
    logger: logging.Logger
    process: Optional[ServerProcess]
    server_config: ServerConfig
    _status: ServerStatus
    properties: ServerProperties
    _mcstatus_server: Optional[JavaServer]

    def __init__(self, server_config: ServerConfig):
        self.logger = logging.getLogger(f"{self.__class__.__name__} {server_config.name}")
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

    def start(self):
        if self.is_running:
            raise ServerAlreadyRunningException()
        if self._status == ServerStatus.NOT_INSTALLED or self._status == ServerStatus.INSTALLING:
            raise ServerNotInstalledException()
        jar_path = os.path.join(self.server_config.path, "server.jar")
        if not os.path.exists(jar_path):
            raise FileNotFoundError()
        self.logger.info("Starting server")
        command = ["java", f"-Xmx{self.server_config.ram}M", f"-Xms{self.server_config.ram}M", "-jar",
                   jar_path, "--nogui"]
        self.process = ServerProcess(command, cwd=self.server_config.path, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, universal_newlines=True
                                     )
        self.process.callbacks.stdout.add_callback(self._update_status_callback)
        self._start_process_loop()
        self.logger.info("Start event loop")
        self._status = ServerStatus.STARTING

    def stop(self):
        if self.is_online:
            self._send_command("stop")
            self._status = ServerStatus.STOPPING
        else:
            self.logger.warning("Server not running")

    def kill(self):
        if self.is_running:
            self.logger.info("Killing server process")
            self.process.kill()
            self._status = ServerStatus.STOPPED

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
        if not self.properties.get("enable-query"):
            return []
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

    def send_command(self, command: str):
        if self.is_online:
            if command.startswith("/"):
                command = command.lstrip("/")

            self._send_command(command)

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.is_running()

    @property
    def is_online(self) -> bool:
        return self.is_running and self._status == ServerStatus.RUNNING

    def _send_command(self, command):
        self.logger.info(f"Sending command {command} to server")
        self.process.send_input(command)

    def _start_process_loop(self):
        thrd = Thread(target=self.process.read_output)
        thrd.daemon = True
        thrd.start()

    def _update_status_callback(self, output: str):
        if self._status == ServerStatus.STARTING:
            if "For help, type \"help\"" in output:
                if self.properties.get("enable-query"):
                    self._mcstatus_server = JavaServer("localhost", self.properties.get("server-port"))
                self.set_status(ServerStatus.RUNNING)
        if self._status == ServerStatus.STOPPING:
            if "ThreadedAnvilChunkStorage: All dimensions are saved" in output:
                self._mcstatus_server = None
                self.set_status(ServerStatus.STOPPED)
