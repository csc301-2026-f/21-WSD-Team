from .models import Drive, Process, DriveMetric, ProcessMetric
from .collector import DiskIOCollector, ProcessIOCollector

from .os_command_api import *


class LinuxBackend:
    def __init__(self, host_id: str):
        self.host_id = host_id

        self._started = False

        self.disk_collector = DiskIOCollector(tuple(self.list_devices()))
        self.process_collector = ProcessIOCollector()

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

    def refresh_disk_collect(self) -> None:

        if not self._started:
            return
        self.disk_collector.stop()
        self.disk_collector = DiskIOCollector(tuple(self.list_devices()))
        self.disk_collector.start()

    def list_devices(self) -> list[Drive]:
        return get_all_drive()

    def list_processes(self) -> list[Process]:
        if not self._started:
            return []
        return get_all_process()

    def get_device_io(self, interval_seconds: int, device_name: str) -> DriveMetric | None:
        if not self._started:
            return None
        return self.disk_collector.get_metric(interval_seconds, device_name)

    """def sample_process_io(self, interval_seconds: int, pid: int) -> ProcessMetric | None:
        if not self._started:
            return None"""

    def get_pid_io(self, pid: int) -> ProcessMetric | None:
        return get_process_io(pid)

"""    def get_file_io(self, file_path: str, interval_seconds: int):
        if not self._started:
            return None"""