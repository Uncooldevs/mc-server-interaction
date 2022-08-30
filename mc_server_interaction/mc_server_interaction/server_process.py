import asyncio
from asyncio.subprocess import Process
from typing import Callable, Optional

import psutil


class Callback:
    def __init__(self):
        self.installed_callbacks = []

    def __call__(self, *args, **kwargs):
        for func in self.installed_callbacks:
            func(*args, **kwargs)

    def add_callback(self, func: Callable):
        self.installed_callbacks.append(func)


class Callbacks:
    stdout = Callback()
    exit = Callback()
    error_occurred = Callback()


class ServerProcess:
    process: Optional[Process]
    psutil_proc: Optional[psutil.Process]
    callbacks = Callbacks()
    system_metrics: dict = {}
    num_cpus = psutil.cpu_count()
    stdout_since_last_send = ""
    logs = ""

    async def start(self, command, cwd):
        self.process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        self.psutil_proc = psutil.Process(self.process.pid)

    async def read_output(self):
        while self.is_running():
            output = await self.process.stdout.readline()
            if output:
                output = output.decode("utf-8")
                output = output.rstrip("\n")
                self.stdout_since_last_send += output
                self.logs += output
                self.callbacks.stdout(output)
        self.callbacks.exit(self.process.returncode, await self.process.stdout.read())
        self.psutil_proc = None

    def kill(self):
        self.process.kill()
        self.psutil_proc = None

    def is_running(self):
        return self.process.returncode is None

    async def send_input(self, inp: str):
        if not inp.endswith("\n"):
            inp += "\n"
        self.process.stdin.write(inp.encode("utf-8"))
        await self.process.stdin.drain()

    def get_resource_usage(self):
        memory_system = psutil.virtual_memory()
        memory_server = self.psutil_proc.memory_full_info()
        self.system_metrics = {
            "cpu": {
                "percent": round(self.psutil_proc.cpu_percent() / self.num_cpus, 2)
            },
            "memory": {
                "total": memory_system.total,
                "used": memory_system.used,
                "server": memory_server.uss
            }
        }
        return self.system_metrics
