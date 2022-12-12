import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Dict

import aiofiles

from mc_server_interaction.interaction import MinecraftServer
from mc_server_interaction.paths import backup_dir, data_dir


@dataclass
class Backup:
    sid: str
    time: datetime
    world: str
    version: str
    path: str
    size: int = 0

    @property
    def __dict__(self):
        return {
            "sid": self.sid,
            "time": self.time.timestamp(),
            "world": self.world,
            "version": self.version,
            "path": self.path,
            "size": self.size
        }

    @classmethod
    def from_json(cls, data: Dict):
        return cls(
            sid=data["sid"],
            time=datetime.fromtimestamp(data["time"]),
            world=data["world"],
            version=data["version"],
            path=data["path"],
            size=data.get("size", 0)
        )


class BackupManager:
    file_name = str(data_dir / "backups.json")

    def __init__(self, servers: Dict[str, MinecraftServer]):
        self.logger = getLogger(f"MCServerInteraction.{self.__class__.__name__}")
        self.servers = servers
        self.backups: Dict[str, Backup] = {}
        self.load_backups()

    def load_backups(self):
        self.logger.info("Loading backup file")
        try:
            with open(self.file_name, "r") as f:
                backups = json.load(f)
                self.backups = {
                    bid: Backup.from_json(backup) for bid, backup in backups.items()
                }
        except (json.decoder.JSONDecodeError, FileNotFoundError):
            data = {}
            for i in self.servers:
                data[i] = []

    def save_backup_file(self):
        self.logger.info("Saving backup file")
        with open(self.file_name, "w") as f:
            json.dump(
                {
                    bid: backup.__dict__ for bid, backup in self.backups.items()
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
        bid = str(uuid.uuid4().hex)
        file_name = str(backup_dir / f"{str(bid)}.zip")
        world.backup(str(backup_dir / bid))
        size = Path(file_name).stat().st_size

        self.backups[bid] = Backup(
            sid, datetime.now(), world_name, server.server_config.version, file_name, size
        )
        self.save_backup_file()

    async def restore_backup(self, bid):
        # throws key error
        backup = self.backups[bid]
        server = self.servers[backup.sid]

        if server.is_running and server.active_world.name == backup.world:
            self.logger.info("Stopping server to restore backup")
            await server.shutdown()
        self.logger.info(f"Restoring backup for {backup.sid}: {backup.world}")
        world = server.get_world(backup.world)

        restart = False
        if server.active_world.name == world.name:
            await server.shutdown()
            restart = True

        world.restore_backup(backup_dir / f"{bid}.zip")
        if restart:
            await server.start()

    def delete_backup(self, bid: str):
        backup = self.backups.pop(bid)
        if backup is None:
            return

        os.remove(backup.path)
        self.save_backup_file()

    def get_backup(self, bid: str):
        return self.backups.get(bid, None)

    def get_backups_for_server(self, sid: str):
        return {
            bid: backup for bid, backup in self.backups.items() if sid == backup.sid
        }

    def auto_schedule(self):
        # TODO
        pass
