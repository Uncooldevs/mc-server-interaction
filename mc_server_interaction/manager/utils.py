import datetime
import json
import logging
import os
from typing import List

import aiofiles
import aiohttp
from bs4 import BeautifulSoup

from mc_server_interaction.exceptions import UnsupportedVersionException
from mc_server_interaction.paths import data_dir


class AvailableMinecraftServerVersions:
    logger: logging.Logger
    filename = str(data_dir / "minecraft_versions.json")

    def __init__(self):
        self.logger = logging.getLogger(
            f"MCServerInteraction.{self.__class__.__name__}"
        )
        self.available_versions = {}
        # print(self.available_versions)

    async def load(self):
        await self._get_available_minecraft_versions()

    async def _get_webpage(self, url) -> str:
        self.logger.debug("Retrieving webpage")
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux i686; rv:96.0) Gecko/20100101 Firefox/96.0"
        }
        async with aiohttp.ClientSession() as session:
            return await (await session.get(url, headers=headers)).text()

    async def _get_available_minecraft_versions(self):
        if os.path.exists(self.filename):
            async with aiofiles.open(self.filename, "r") as f:
                data = json.loads(await f.read())
            timestamp = data["timestamp"]
            timestamp = datetime.datetime.fromtimestamp(float(timestamp))
            diff = datetime.datetime.now() - timestamp
            if diff.days <= 7:
                self.logger.debug("Load cached Minecraft versions")
                self.available_versions = data["versions"]
                return

        self.logger.debug("Updating Minecraft versions")
        webpage = await self._get_webpage("https://mcversions.net")
        soup = BeautifulSoup(webpage, "html.parser")
        releases = soup.find_all(
            "div",
            {
                "class": "item flex items-center p-3 border-b border-gray-700 snap-start ncItem"
            },
        )
        for version in releases:
            version_link = version.find("a", text="Download").get("href")
            if (
                    not version_link.startswith("/download/b")
                    and not version_link.startswith("/download/a")
                    and version_link != "/download/1.1"
                    and not version_link.startswith("/download/1.0")
                    and not version_link.startswith("/download/c")
                    and not version_link.startswith("/download/rd")
                    and not version_link.startswith("/download/inf")
            ):
                self.available_versions[
                    version.get("id")
                ] = "https://mcversions.net" + version.find("a", text="Download").get(
                    "href"
                )
        self.logger.debug(f"Retrieved info for {len(self.available_versions)} server versions")
        async with aiofiles.open(self.filename, "w") as f:
            data = {
                "versions": self.available_versions,
                "timestamp": str(datetime.datetime.now().timestamp()),
            }
            await f.write(json.dumps(data, indent=4))

    async def get_download_link(self, version: str):
        if version == "latest":
            version = list(self.available_versions.keys())[0]
        self.logger.debug(
            f"Retrieving download link for server jar for version {version}"
        )
        url = self.available_versions.get(version)
        if url is None:
            raise UnsupportedVersionException()
        webpage = await self._get_webpage(url)
        soup = BeautifulSoup(webpage, "html.parser")
        download_button = soup.find("a", text="Download Server Jar")
        download_link = download_button.get("href")
        # print(download_button.get("download"))
        return download_link

    def get_latest_version(self):
        return list(self.available_versions.keys())[0]

    def get_version_list(self) -> List[str]:
        return ["latest"] + list(self.available_versions.keys())


class DataVersionMapping:
    logger: logging.Logger
    filename = str(data_dir / "data_versions.json")

    def __init__(self):
        self.logger = logging.getLogger(
            f"MCServerInteraction.{self.__class__.__name__}"
        )
        self.data_versions = {}
