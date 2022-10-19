import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Dict, List

from mc_server_interaction.interaction import MinecraftServer
from mc_server_interaction.paths import backup_dir, data_dir


@dataclass
class Backup:
    time: datetime
    world: str
    version: str
    path: str

    def __dict__(self):
        return {
            "time": self.time.timestamp(),
            "world": self.world,
            "version": self.version,
            "path": self.path
        }

    @classmethod
    def from_json(cls, data: Dict):
        return cls(
            time=datetime.fromtimestamp(data["time"]),
            world=data["world"],
            version=data["version"],
            path=data["path"]
        )


class BackupManager:
    file_name = str(data_dir / "backups.json")

    def __init__(self, servers: Dict[str, MinecraftServer]):
        self.logger = getLogger(f"MCServerInteraction.{self.__class__.__name__}")
        self.servers = servers
        self.backups: Dict[str, List[Backup]] = {}
        self.load_backups()
        print(self.backups)

    def load_backups(self):
        self.logger.info("Loading backup file")
        try:
            with open(self.file_name, "r") as f:
                backups = json.load(f)
                self.backups = {
                    key: [Backup.from_json(backup) for backup in backup_list] for key, backup_list in backups.items()
                }
        except (json.decoder.JSONDecodeError, FileNotFoundError):
            data = {}
            for i in self.servers:
                data[i] = []

    def save_backups(self):
        self.logger.info("Saving backup file")
        with open(self.file_name, "w") as f:
            json.dump(
                {
                    sid: [backup.__dict__() for backup in backup_list] for sid, backup_list in self.backups.items()
                },
                f, indent=4,
            )

    async def create_backup(self, sid: str, world_name):
        server = self.servers[sid]
        if server.is_running and server.active_world.name == world_name:
            self.logger.info("Stopping server to create backup")
            await server.shutdown()

        self.logger.info(f"Creating backup for {sid}: {world_name}")
        world = server.get_world(world_name)
        file_name = str(backup_dir / f"{sid}_{world.name}_{datetime.now().strftime('%y-%m-%d--%H-%M-%S')}")
        world.backup(file_name)
        if sid not in self.backups.keys():
            self.backups[sid] = []

        self.backups[sid].append(
            Backup(
                datetime.now(), world_name, server.server_config.version, file_name + ".zip"
            ))
        self.save_backups()

    async def restore_backup(self, sid, world_name):
        server = self.servers[sid]
        if server.is_running and server.active_world.name == world_name:
            self.logger.info("Stopping server to restore backup")
            await server.shutdown()
        self.logger.info(f"Restoring backup for {sid}: {world_name}")
        world = server.get_world(world_name)
        world.restore_backup(backup_dir / f"{sid}_{world.name}_{datetime.now().strftime('%y-%m-%d--%H-%M-%S')}")

    def get_backup(self, sid):
        return self.backups.get(sid, [])

    def auto_schedule(self):
        # Later
        pass
