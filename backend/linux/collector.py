from collections import deque
import threading
import time


from . import constants
from .models import DriveMetric, ProcessMetric, Drive, Process
from .os_command_api import sample_all_drive


class DiskIOCollector:
    def __init__(self, drives: tuple[Drive]):
        self._history = deque(maxlen=constants.MAX_DRIVE_SAMPLE_HISTORY_LENGTH)
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._drives = drives
        self._drive_names = tuple([i.device_id for i in self._drives])

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._fetch_data_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _fetch_data_loop(self) -> None:
        next_sample = time.monotonic()

        while not self._stop_event.is_set():
            with self._lock:
                self._history.append(sample_all_drive(self._drive_names))
            next_sample += 1

            sleep_time = max(0, next_sample - time.monotonic())
            self._stop_event.wait(sleep_time)

    def get_metric(self, time_interval: int, device_name: str) -> DriveMetric | None:
        if time_interval <= 0 or device_name not in self._drive_names:
            return None

        with self._lock:
            if len(self._history) <= time_interval:
                return None
            latest_batch = self._history[-1]
            older_batch = self._history[-(time_interval + 1)]

        latest = next((s for s in latest_batch if s.device_id == device_name), None)
        older = next((s for s in older_batch if s.device_id == device_name), None)
        if latest is None or older is None:
            return None

        return DriveMetric(
            timestamp=older.timestamp,
            duration=time_interval,
            read_bytes=(latest.sectors_read - older.sectors_read) * 512,
            write_bytes=(latest.sectors_write - older.sectors_write) * 512,
            read_count=latest.reads_complete - older.reads_complete,
            write_count=latest.writes_complete - older.writes_complete,
        )


class ProcessIOCollector:

    # TODO

    def __init__(self):
        self._history = deque(maxlen=constants.MAX_DRIVE_SAMPLE_HISTORY_LENGTH)
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._fetch_data_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _fetch_data_loop(self) -> None:
        next_sample = time.monotonic()

        while not self._stop_event.is_set():
            with self._lock:
                self._history.append()
            next_sample += 1

            sleep_time = max(0, next_sample - time.monotonic())
            self._stop_event.wait(sleep_time)

    def get_metric(self, time_interval: float, pid: str) -> ProcessMetric:
        pass
