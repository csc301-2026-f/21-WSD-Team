from .models import Drive, Process, DriveMetric, ProcessMetric, ErrorCode
from .collector import DiskIOCollector, ProcessIOCollector

from .process import get_all_process
from .drive import get_all_drive


class LinuxBackend:
    def __init__(self, host_id: str):
        self.host_id = host_id

        self._started = False

        self.disk_collector = DiskIOCollector(tuple(self.list_devices()))
        self.process_collector = ProcessIOCollector()

    def start(self) -> None:
        """
        Start background disk and process I/O collection.
        """
        if self._started:
            return

        self.disk_collector.start()
        self.process_collector.start()

        self._started = True

    def close(self) -> None:
        """
        Stop background collection and wait for both threads to terminate.
        """
        if not self._started:
            return

        self.disk_collector.stop()
        self.process_collector.stop()

        self._started = False

    def refresh_disk_collect(self) -> None:
        """
        Rediscover physical drives and restart the disk collector.

        Previous disk sampling history is discarded.
        """
        if not self._started:
            return

        self.disk_collector.stop()
        self.disk_collector = DiskIOCollector(tuple(self.list_devices()))
        self.disk_collector.start()

    def list_devices(self) -> list[Drive]:
        """
        Retrieve physical storage devices detected by Linux.

        :return: List of Drive objects, or an empty list if none are found
        """
        return get_all_drive()

    def list_processes(self) -> list[Process]:
        """
        Retrieve currently running processes.

        :return: List of Process objects, or an empty list if the backend
                 is stopped
        """
        if not self._started:
            return []

        return get_all_process()

    def get_device_io(
        self, interval_seconds: int, device_name: str
    ) -> DriveMetric | None:
        """
        Retrieve disk I/O statistics from previously collected samples.
        Does not block while waiting for new samples.

        :param interval_seconds: Number of one-second sampling intervals to compare; must be positive
        :param device_name: Linux block device ID, e.g. "nvme0n1"
        :return: DriveMetric containing interval I/O statistics, or None if stopped, device is invalid,
                 or history is insufficient
        """
        if not self._started:
            return None

        return self.disk_collector.get_metric(interval_seconds, device_name)

    def get_process_io(
        self, interval_seconds: int, pid: int
    ) -> ProcessMetric | None:
        """
        Retrieve process I/O statistics from previously collected samples.
        Process must exist in both samples being compared.

        :param interval_seconds: Number of one-second sampling intervals to compare; must be positive
        :param pid: Linux process ID
        :return: ProcessMetric containing interval I/O statistics, or None if stopped, history is insufficient,
                 process is unavailable, or access is denied
        """
        if not self._started:
            return None

        rtn = self.process_collector.get_metric(interval_seconds, pid)
        if isinstance(rtn, ErrorCode):
            return None
        else:
            return rtn


"""    def get_all_process_io(self, interval_seconds: int) -> list[ProcessMetric]:
        if not self._started:
            return None

    def get_all_drive_io(self, interval_seconds: int) -> list[DriveMetric]:
        if not self._started:
            return None"""
