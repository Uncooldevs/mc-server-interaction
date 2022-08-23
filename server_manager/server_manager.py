import json
import os
import shutil
from typing import Dict
import requests

from server_manager.utils import AvailableMinecraftServerVersions
from mc_server_interaction import MinecraftServer
from mc_server_interaction.models import DirectoryNotEmptyException


class ServerManager:
    server_list: Dict[str, MinecraftServer]
    data_file = "manager_data.json"
    _manager_data = {}
    available_versions = AvailableMinecraftServerVersions()

    def __init__(self):
        self.server_list = {}
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                self._manager_data = json.load(f)

                for server in self._manager_data["servers"]:
                    self.server_list[server["name"]] = MinecraftServer(**server)

    def start_server(self, sid):
        self.server_list.get(sid).start()

    def stop_server(self, sid):
        self.server_list.get(sid).start()

    def create_new_server(self, name, path, version):
        if not os.path.exists(path):
            os.makedirs(path)
        if len(os.listdir(path)) > 0:
            raise DirectoryNotEmptyException(f"Directory {path} is not empty")
        if os.path.exists(f"cache/minecraft_server_{version}.jar"):
            shutil.copy(f"cache/minecraft_server_{version}.jar", path)

        else:
            download_url = self.available_versions.get_download_link(version)
            resp = requests.get(download_url)
            if resp.status_code == 200:
                with open(f"cache/minecraft_server_{version}.jar", "wb") as f:
                    f.write(resp.content)
                shutil.copy(f"cache/minecraft_server_{version}.jar", path)

