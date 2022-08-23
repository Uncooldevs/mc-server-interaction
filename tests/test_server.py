import os
import time

from server_manager.mc_server_interaction import MinecraftServer, HardwareConfig, PathConfig


def print_console(output: str):
    print(output)


def test_server_start():
    hardware_config = HardwareConfig(ram=2048)
    server_path = os.path.join(os.path.dirname(os.getcwd()), "test_servers/1.19.2")
    print(server_path)
    path_config = PathConfig(base_path=server_path, jar_path=os.path.join(server_path, "server.jar"))
    server = MinecraftServer(hardware_config, path_config)
    server.start()
    server.process.callbacks.stdout.add_callback(print_console)
    time.sleep(120)
    server.stop()
