import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from server_manager.server_manger import game_constants


class ServerStatus(Enum):
    STOPPED = 0
    RUNNING = 1
    STARTING = 2
    STOPPING = 3
    INSTALLING = 4
    NOT_INSTALLED = 5


@dataclass
class Player:
    name: str
    is_online: bool = False
    is_op: Optional[bool] = False
    is_banned: Optional[bool] = False
    ban_reason: Optional[str] = None
    ban_since: Optional[str] = None


@dataclass
class ServerConfig:
    path: str
    name: str
    version: str
    ram: int = 2048
    created_at: float = time.time()


@dataclass
class WorldGenerationSettings:
    level_seed: str = ""
    level_type: str = game_constants.LevelTypes.DEFAULT
    generate_structures: bool = False
    world_name: str = "worlds/world"

    def __iter__(self):
        return iter([
            ("level-seed", self.level_seed),
            ("level-type", self.level_type),
            ("generate-structures", self.generate_structures),
            ("world-name", self.world_name)
        ])
