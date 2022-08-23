import datetime
import json
import os.path

import requests
from bs4 import BeautifulSoup


class AvailableMinecraftServerVersions:

    def __init__(self):
        self.available_versions = {}
        self._get_available_minecraft_versions()  # load on init
        print(self.available_versions)

    def _get_webpage(self, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux i686; rv:96.0) Gecko/20100101 Firefox/96.0"
        }
        return requests.get(url, headers=headers).text

    def _get_available_minecraft_versions(self):

        if os.path.exists("minecraft_versions.json"):
            with open("minecraft_versions.json", "r") as f:
                data = json.load(f)
            timestamp = data["timestamp"]
            timestamp = datetime.datetime.fromtimestamp(float(timestamp))
            diff = datetime.datetime.now() - timestamp
            if diff.days <= 7:
                print("Load cached")
                self.available_versions = data["versions"]
                return

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
        with open("minecraft_versions.json", "w") as f:
            data = {
                "versions": self.available_versions,
                "timestamp": str(datetime.datetime.now().timestamp())
            }
            json.dump(data, f, indent=4)

    def get_download_link(self, version: str):
        url = self.available_versions[version]
        webpage = self._get_webpage(url)
        soup = BeautifulSoup(webpage, "html.parser")
        download_button = soup.find("a", text="Download Server Jar")
        download_link = download_button.get("href")
        #print(download_button.get("download"))
        return download_link

if __name__ == '__main__':
    print(AvailableMinecraftServerVersions().get_download_link("1.19.2"))