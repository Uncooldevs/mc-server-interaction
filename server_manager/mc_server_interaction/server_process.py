from typing import Callable

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
    metrics_update = Callback()


class ServerProcess(psutil.Popen):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stdout_since_last_send = ""
        self.logs = ""
        self.data = {}
        self.num_cpus = psutil.cpu_count()
        self.stop = False
        self.callbacks = Callbacks

    def read_output(self):
        while not self.stop and self.is_running():
            output = self.stdout.readline()
            if output:
                print(output)
                output = output.rstrip("\n")
                self.stdout_since_last_send += output
                self.logs += output
                self.callbacks.stdout(output)
        self.callbacks.exit(self.returncode, self.stdout.read())

    def send_input(self, inp: str):
        if not inp.endswith("\n"):
            inp += "\n"
        self.stdin.write(inp)
        self.stdin.flush()

    def get_resource_usage(self):
        memory_system = psutil.virtual_memory()
        memory_server = self.memory_full_info()
        self.data = {
            "cpu": {
                "percent": round(self.cpu_percent() / self.num_cpus, 2)
            },
            "memory": {
                "total": memory_system.total,
                "used": memory_system.used,
                "server": memory_server.uss
            }
        }
        self.callbacks.metrics_update(self.data)
        return self.data
