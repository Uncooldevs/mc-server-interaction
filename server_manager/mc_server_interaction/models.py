from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


@dataclass
class HardwareConfig:
    ram: int


@dataclass
class PathConfig:
    base_path: str
    jar_path: str


@dataclass
class MinecraftServerNetworkConfig:
    port: int


class ServerStatus(Enum):
    RUNNING = auto
    STOPPED = auto
    STARTING = auto
    STOPPING = auto
    INSTALLING = auto
    NOT_INSTALLED = auto


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
    created_at: int
    installed: bool


class DirectoryNotEmptyException(Exception):
    pass