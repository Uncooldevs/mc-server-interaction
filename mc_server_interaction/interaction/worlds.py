import json
from pathlib import Path

from mc_server_interaction.exceptions import NotAWorldFolderException
from mc_server_interaction.server_manger.utils import async_copytree


class MinecraftWorld:
    name: str
    path: Path
    version: str
    type: str

    def __init__(self, path: Path, version: str = None):
        self.path = path
        if not self.exists():
            raise NotAWorldFolderException()
        self.name = self.path.name
        self.version = version
        self.type = None
        if version is None:
            self._load_version()

    def to_dict(self):
        return {
            "name": self.name,
            "path": str(self.path),
            "version": self.version,
            "type": self.type
        }

    def exists(self):
        if self.path.is_dir():
            must_contain = ["level.dat", "session.lock", "playerdata", "data", "DIM1", "DIM-1", "region"]
            for entry in must_contain:
                if not (self.path/entry).exists():
                    return False
            return True
        return False

    def _load_version(self):
        advancements_dir = (self.path/"advancements")
        stats_dir = (self.path/"stats")
        for d in [advancements_dir, stats_dir]:
            if d.is_dir():
                files = [f for f in advancements_dir.iterdir() if str(f).endswith(".json")]
                if len(files) > 0:
                    with open(d/files[0], "r") as f:
                        data = json.load(f)
                    if type(data.get("DataVersion")) is int:
                        break

    async def copy_to(self, destination: Path, override: bool = False):
        if not self.exists():
            raise NotAWorldFolderException()
        if destination.is_dir():
            if any(destination.iterdir()) and not override:
                raise IsADirectoryError()
        else:
            destination.mkdir()
        await async_copytree(self.path, destination)

    async def copy_to_server(self, server, override: bool = False):
        path = Path(server.server_config.path) / "worlds" / self.name
        if not path.is_dir():
            path.mkdir(parents=True)
        await self.copy_to(path)
        server.load_worlds()
