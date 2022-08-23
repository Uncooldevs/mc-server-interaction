from dataclasses import dataclass
from enum import Enum, auto


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
