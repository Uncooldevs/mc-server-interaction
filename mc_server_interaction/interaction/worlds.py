import json
import shutil
from logging import getLogger
from pathlib import Path

from mc_server_interaction.exceptions import NotAWorldFolderException
from mc_server_interaction.utils.files import async_copytree


class MinecraftWorld:
    name: str
    path: Path
    version: str
    type: str

    def __init__(self, path: Path, server_name: str, version: str = None):
        self.logger = getLogger(f"MCServerInteraction.{self.__class__.__name__}:{server_name}:{path.name}")

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
                if not (self.path / entry).exists():
                    return False
            return True
        return False

    def _load_version(self):
        self.logger.debug("Attempting to load Minecraft version from world files")
        advancements_dir = (self.path / "advancements")
        stats_dir = (self.path / "stats")
        for d in [advancements_dir, stats_dir]:
            if d.is_dir():
                files = [f for f in advancements_dir.iterdir() if str(f).endswith(".json")]
                if len(files) > 0:
                    with open(d / files[0], "r") as f:
                        data = json.load(f)
                    if type(data.get("DataVersion")) is int:
                        break

    def backup(self, target_path: str):
        self.logger.info(f"Creating backup to path {target_path}")
        shutil.make_archive(
            target_path, "zip",
            str(self.path)
        )

    def restore_backup(self, zip_path):
        self.logger.info(f"Restoring backup from {zip_path}")
        if self.path.is_dir():
            shutil.rmtree(str(self.path))

        shutil.unpack_archive(zip_path, self.path, "zip")
        self.logger.info("Backup archive unpacked")

    async def copy_to(self, destination: Path, override: bool = False):
        self.logger.debug(f"Copying world to path {destination}")
        if not self.exists():
            raise NotAWorldFolderException()
        if destination.is_dir():
            if any(destination.iterdir()) and not override:
                raise IsADirectoryError()
        else:
            destination.mkdir()
        await async_copytree(self.path, destination)

    async def copy_to_server(self, server, override: bool = False):
        self.logger.info(f"Copying world to server {server.server_config.name}")
        path = Path(server.server_config.path) / "worlds" / self.name
        if not path.is_dir():
            path.mkdir(parents=True)
        await self.copy_to(path)
        server.load_worlds()
