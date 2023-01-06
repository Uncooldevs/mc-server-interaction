import asyncio
import os
from asyncio.subprocess import PIPE
from dataclasses import dataclass

import aiofiles
import aiohttp

from mc_server_interaction.paths import data_dir, cache_dir

BUILD_TOOLS_URL = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
__FILE_NAME = data_dir / "spigot_versions.json"
BUILD_TOOL_PATH = data_dir / "build"


@dataclass
class SpigotFile:
    path: str
    version: str


class SpigotManager:
    def __init__(self):
        self._data = {}
        if not BUILD_TOOL_PATH.exists():
            os.makedirs(BUILD_TOOL_PATH)

    async def download_build_tools(self):
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(BUILD_TOOL_PATH / "BuildTools.jar", "wb") as f:
                resp = await session.get(BUILD_TOOLS_URL)
                async for chunk in resp.content.iter_chunked(10 * 1024):
                    await f.write(chunk)

    async def build_spigot(self, version: str):
        proc = await asyncio.create_subprocess_exec("java",
                                                    *f"-jar {BUILD_TOOL_PATH / 'BuildTools.jar'} --rev {version} -o {BUILD_TOOL_PATH}".split(
                                                        " "), stdout=PIPE, cwd=BUILD_TOOL_PATH)

        if "Success! Everything completed successfully" in (
                out := (await proc.stdout.read()).decode("utf-8", errors="ignore")):
            print(out)
            print("Fertig!!!")


if __name__ == '__main__':
    x = SpigotManager()
    asyncio.run(x.build_spigot("1.19.2"))
