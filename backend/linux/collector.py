# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from collections import deque
import threading
import time

from .constants import *
from .models import DriveMetric, ProcessMetric, Drive, ErrorCode
from .drive import sample_all_drive
from .process import sample_all_process


class DiskIOCollector:
    def __init__(self, drives: tuple[Drive]):
        self._history = deque(maxlen=MAX_DRIVE_SAMPLE_HISTORY_LENGTH)
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
            self._thread.join()

    def _fetch_data_loop(self) -> None:
        next_sample = time.monotonic()

        while not self._stop_event.is_set():
            sample = sample_all_drive(self._drive_names)
            with self._lock:
                self._history.append(sample)
            next_sample += 1

            sleep_time = next_sample - time.monotonic()
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
            read_bytes=(latest.sectors_read - older.sectors_read) * BYTES_IN_SECTOR,
            write_bytes=(latest.sectors_write - older.sectors_write) * BYTES_IN_SECTOR,
            read_count=latest.reads_complete - older.reads_complete,
            write_count=latest.writes_complete - older.writes_complete,
        )


class ProcessIOCollector:
    def __init__(self):
        self._history = deque(maxlen=MAX_PROCESS_SAMPLE_HISTORY_LENGTH)
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
            self._thread.join()

    def _fetch_data_loop(self) -> None:
        next_sample = time.monotonic()

        while not self._stop_event.is_set():
            sample = sample_all_process()
            with self._lock:
                self._history.append(sample)
            next_sample += 1

            sleep_time = max(0, next_sample - time.monotonic())
            self._stop_event.wait(sleep_time)

    def get_metric(self, time_interval: int, pid: int) -> ProcessMetric | ErrorCode:

        if time_interval <= 0:
            raise ValueError("time interval must be positive")

        with self._lock:
            if len(self._history) <= time_interval:
                return ErrorCode.INVALID_TIME_INTERVAL
            latest_batch = self._history[-1]
            older_batch = self._history[-(time_interval + 1)]

        latest = next((s for p, s in latest_batch.items() if p.pid == pid), None)
        older = next((s for p, s in older_batch.items() if p.pid == pid), None)
        if latest is None or older is None:
            return ErrorCode.PROCESS_NOT_FOUND

        if latest.process != older.process:
            return ErrorCode.PROCESS_PID_REUSED

        return ProcessMetric(
            timestamp=older.timestamp,
            duration=time_interval,
            read_bytes=latest.read_bytes - older.read_bytes,
            write_bytes=latest.write_bytes - older.write_bytes,
            reads_complete=latest.reads_complete - older.reads_complete,
            writes_complete=latest.writes_complete - older.writes_complete,
        )
