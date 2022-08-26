import datetime
import json
import logging
import os

import requests
from bs4 import BeautifulSoup

from server_manager.exceptions import UnsupportedVersionException
from server_manager.paths import data_dir


class AvailableMinecraftServerVersions:
    logger: logging.Logger
    filename = str(data_dir / "minecraft_versions.json")

    def __init__(self):
        self.logger = logging.getLogger(f"MCServerInteraction.{self.__class__.__name__}")
        self.available_versions = {}
        self._get_available_minecraft_versions()  # load on init
        # print(self.available_versions)

    def _get_webpage(self, url):
        self.logger.debug("Retrieving webpage")
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux i686; rv:96.0) Gecko/20100101 Firefox/96.0"
        }
        return requests.get(url, headers=headers).text

    def _get_available_minecraft_versions(self):

        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                data = json.load(f)
            timestamp = data["timestamp"]
            timestamp = datetime.datetime.fromtimestamp(float(timestamp))
            diff = datetime.datetime.now() - timestamp
            if diff.days <= 7:
                self.logger.debug("Load cached Minecraft versions")
                self.available_versions = data["versions"]
                return

        self.logger.debug("Updating Minecraft versions")
        webpage = self._get_webpage("https://mcversions.net")
        soup = BeautifulSoup(webpage, "html.parser")
        releases = soup.find_all("div",
                                 {"class": "item flex items-center p-3 border-b border-gray-700 snap-start ncItem"})
        for version in releases:
            version_link = version.find("a", text="Download").get("href")
            if not version_link.startswith("/download/b") and not version_link.startswith("/download/a") \
                    and version_link != "/download/1.1" and not version_link.startswith("/download/1.0") \
                    and not version_link.startswith("/download/c") and not version_link.startswith("/download/rd") \
                    and not version_link.startswith("/download/inf"):
                self.available_versions[version.get("id")] = "https://mcversions.net" \
                                                             + version.find("a", text="Download").get("href")
        with open(self.filename, "w") as f:
            data = {
                "versions": self.available_versions,
                "timestamp": str(datetime.datetime.now().timestamp())
            }
            json.dump(data, f, indent=4)

    def get_download_link(self, version: str):
        if version == "latest":
            version = list(self.available_versions.keys())[0]
        self.logger.debug(f"Retrieving download link for server jar for version {version}")
        url = self.available_versions.get(version)
        if url is None:
            raise UnsupportedVersionException()
        webpage = self._get_webpage(url)
        soup = BeautifulSoup(webpage, "html.parser")
        download_button = soup.find("a", text="Download Server Jar")
        download_link = download_button.get("href")
        # print(download_button.get("download"))
        return download_link
