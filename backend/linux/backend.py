from .models import Drive, Process, DriveMetric, ProcessMetric
from collector import DiskIOCollector, ProcessIOCollector

import os_command_api


class LinuxBackend:
    def __init__(self, host_id: str):
        self.host_id = host_id

        self.disk_collector = DiskIOCollector()
        self.process_collector = ProcessIOCollector()

        self._started = False

    def start(self) -> None:
        if self._started:
            return

        self.disk_collector.start()
        self.process_collector.start()

        self._started = True

    def close(self) -> None:
        if not self._started:
            return

        self.disk_collector.stop()
        self.process_collector.stop()

        self._started = False

    def list_devices(self) -> list[Drive]:
        if not self._started:
            return []
        return os_command_api.get_all_drive()

    def list_processes(self) -> list[Process]:
        if not self._started:
            return []
        return os_command_api.get_all_process()

    def get_device_io(self, interval_seconds: int, device_name: str) -> DriveMetric | None:
        if not self._started:
            return None
        return self.disk_collector.get_metric(interval_seconds, device_name)

    """def sample_process_io(self, interval_seconds: int, pid: int) -> ProcessMetric | None:
        if not self._started:
            return None"""

    def get_pid_io(self, pid: int) -> ProcessMetric | None:
        return os_command_api.get_process_io(pid)

"""    def get_file_io(self, file_path: str, interval_seconds: int):
        if not self._started:
            return None"""