from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


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
    ram: int
    version: str
    created_at: float
