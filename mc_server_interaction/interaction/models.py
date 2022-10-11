import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union


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


@dataclass
class BannedPlayer(Player):
    banned_since: Optional[float] = 0
    banned_by: Optional[str] = ""
    reason: Optional[str] = ""


@dataclass
class OPPlayer(Player):
    op_level: Optional[int] = 4


@dataclass
class ServerConfig:
    path: str
    name: str
    version: str
    ram: int = 2048
    created_at: float = time.time()
    installed: bool = True

    def set_ram(self, ram: Union[int, str]):
        if isinstance(ram, str):
            ram = int(ram)

        self.ram = ram

    def set_name(self, name):
        self.name = name
