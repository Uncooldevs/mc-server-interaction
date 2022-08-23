import subprocess
from threading import Thread
from typing import Optional

from mc_server_interaction.models import HardwareConfig, PathConfig, ServerStatus
from mc_server_interaction.process_handler import ServerProcess


class MinecraftServer:
    process: Optional[ServerProcess]
    hardware_config: HardwareConfig
    path_data: PathConfig
    _status: ServerStatus

    def __init__(self, hardware_config: HardwareConfig, path_data: PathConfig):
        self.hardware_config = hardware_config
        self.path_data = path_data

        self._status = ServerStatus.STOPPED

    def start(self):
        command = ["java", f"-Xmx{self.hardware_config.ram}M", f"-Xms{self.hardware_config.ram}M", "-jar",
                   self.path_data.jar_path, "--nogui"]
        self.process = ServerProcess(command, cwd=self.path_data.base_path, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, universal_newlines=True
                                     )
        self.process.callbacks.stdout.add_callback(self._update_status)
        self._start_process_loop()
        self._status = ServerStatus.STARTING

    def stop(self):
        if self.is_online():
            self._send_command("stop")
            self._status = ServerStatus.STOPPING

    def kill(self):
        if self.is_running():
            self.process.kill()
        self._status = ServerStatus.STOPPED

    def get_status(self) -> ServerStatus:
        return self._status

    def get_system_load(self):
        if self.is_running():
            return self.process.get_resource_usage()

    def send_command(self, command: str):
        if self.is_online():
            if command.startswith("/"):
                command = command.lstrip("/")

            self._send_command(command)

    def is_running(self) -> bool:
        return self.process is not None and self.process.is_running()

    def is_online(self) -> bool:
        return self.is_running() and self._status == ServerStatus.RUNNING

    def _send_command(self, command):
        self.process.send_input(command)

    def _start_process_loop(self):
        thrd = Thread(target=self.process.read_output)
        thrd.daemon = True
        thrd.start()

    def _update_status(self, output: str):
        if self._status == ServerStatus.STARTING:
            if "For help, type \"help\"" in output:
                self._status = ServerStatus.RUNNING

