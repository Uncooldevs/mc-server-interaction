import os
import pathlib
import platform

from mc_server_interaction import __app_name__

if platform.system() == "Windows":
    data_dir = pathlib.Path(os.environ["APPDATA"]) / __app_name__
    cache_dir = data_dir.joinpath("cache")
elif platform.system() == "Linux":
    data_dir = pathlib.Path(f"~/.local/share/{__app_name__}").expanduser()
    cache_dir = pathlib.Path(f"~/.cache/{__app_name__}").expanduser()
elif platform.system() == "Darwin":
    data_dir = pathlib.Path(
        f"~/Library/Application Support/{__app_name__}"
    ).expanduser()
    cache_dir = pathlib.Path(f"~/Library/Caches/{__app_name__}").expanduser()
else:
    raise Exception(f"Unsupported platform: {platform.system()}")

if not os.path.exists(data_dir):
    os.makedirs(data_dir)
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

backup_dir = data_dir / "backups"
