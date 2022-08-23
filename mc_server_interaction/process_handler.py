import subprocess
import time
from threading import Thread
from typing import List, Callable

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
        print("start read")
        while not self.stop and self.is_running():
            output = self.stdout.readline()
            if output:
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

    def update_resource_usage(self):
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

    def get_resource_usage(self):
        return self.data


class ProcessHandler(Thread):
    processes = {}
    threads = {}

    def __init__(self):
        super().__init__(target=self.run)
        self.daemon = True
        self.stop = False

    def get_process(self, pid: int):
        return self.processes.get(pid)

    def process_exists(self, pid: int):
        process = self.get_process(pid)
        if process is not None and process.poll() is None:
            return True
        else:
            return False

    def start_process(self, command: List[str], cwd: str):
        process = ServerProcess(command, cwd=cwd,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True
                                )
        pid = process.pid
        self.processes[pid] = process
        thrd = Thread(target=process.read_output)
        thrd.daemon = True
        thrd.start()
        self.threads[pid] = thrd
        return pid, process.callbacks

    def send_input(self, pid: int, message: str):
        process = self.get_process(pid)
        if process is not None:
            process.stdin.write(message)
            process.stdin.flush()

    def run(self) -> None:
        start_time = time.time()
        while not self.stop:
            time.sleep(0.1)
            for pid in list(self.processes.keys()):
                if psutil.pid_exists(pid):
                    process = self.processes[pid]
                    if time.time() - start_time > 3:
                        process.update_resource_usage()
                        start_time = time.time()

                else:
                    self.threads[pid].stop = True
                    del self.threads[pid]
                    del self.processes[pid]
