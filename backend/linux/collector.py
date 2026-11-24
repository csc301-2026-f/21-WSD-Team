# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import stat
import threading
import time

from .constants import *
from .models import DriveMetric, ProcessMetric, Drive, ErrorCode, File, FileSample, FileMetric
from .drive import sample_all_drive
from .process import sample_all_process
from .file import FileIOProbe, COUNTER_FIELDS, resolve_file


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


@dataclass
class _TrackedFile:
    file: File
    slot: int
    kernel_key: tuple[int, int, int] | None = None


class FileIOCollector:
    def __init__(self, probe_factory=FileIOProbe):
        self._probe_factory = probe_factory
        self._probe = None
        self._tracer_failed = False
        self.last_error: Exception | None = None

        self._tracked: dict[str, _TrackedFile] = {}
        self._stat_owners: dict[tuple[int, int], str] = {}
        self._kernel_owners: dict[tuple[int, int, int], str] = {}
        self._free_slots = list(range(MAX_TRACKED_FILES - 1, -1, -1))

        self._history = deque(maxlen=MAX_FILE_SAMPLE_HISTORY_LENGTH)
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> ErrorCode | None:
        if self._thread and self._thread.is_alive():
            return None

        try:
            probe = self._probe_factory()
        except Exception as e:
            with self._lock:
                self._tracer_failed = True
                self.last_error = e
            return ErrorCode.FILE_TRACER_UNAVAILABLE

        with self._lock:
            self._tracer_failed = False
            self.last_error = None
            self._probe = probe
            self._history.clear()
            for path, tracked in self._tracked.items():
                probe.reset(tracked.slot)
                self._bind_locked(path, tracked)

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._fetch_data_loop, daemon=True)
        self._thread.start()
        return None

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None

        with self._lock:
            if self._probe is not None:
                self._probe.close()
                self._probe = None
            self._kernel_owners.clear()
            for tracked in self._tracked.values():
                tracked.kernel_key = None
            self._history.clear()

    def track(self, file_path: str) -> File | ErrorCode:
        file = resolve_file(file_path)
        if isinstance(file, ErrorCode):
            return file

        with self._lock:
            if self._tracer_failed:
                return ErrorCode.FILE_TRACER_UNAVAILABLE
            return self._track_locked(file)

    def track_many(self, file_paths: list[str]) -> tuple[File, ...] | ErrorCode:
        resolved = [resolve_file(path) for path in file_paths]

        files = []
        with self._lock:
            if self._tracer_failed:
                return ErrorCode.FILE_TRACER_UNAVAILABLE
            for file in resolved:
                if isinstance(file, ErrorCode):
                    continue
                result = self._track_locked(file)
                if result is ErrorCode.TRACKING_LIMIT_REACHED:
                    break
                if isinstance(result, File) and result not in files:
                    files.append(result)

        return tuple(files)

    def untrack(self, file: File) -> ErrorCode | None:
        with self._lock:
            tracked = self._tracked.pop(file.absolute_path, None)
            if tracked is None:
                return ErrorCode.FILE_NOT_TRACKED
            self._release_locked(file.absolute_path, tracked)
        return None

    def untrack_many(self, files: tuple[File, ...]) -> ErrorCode | None:
        result = None
        for file in files:
            if self.untrack(file) is not None:
                result = ErrorCode.FILE_NOT_TRACKED
        return result

    def tracked_files(self) -> tuple[File, ...]:
        with self._lock:
            return tuple(tracked.file for tracked in self._tracked.values())

    def sample(self) -> None:
        with self._lock:
            if self._probe is None:
                return

            sizes = self._refresh_locked()
            previous = self._history[-1] if self._history else {}
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            batch = {}
            for path, tracked in self._tracked.items():
                counters = self._probe.read(tracked.slot)
                size = sizes.get(path)
                if size is None:
                    old = previous.get(tracked.file)
                    size = old.size_bytes if old else 0
                batch[tracked.file] = FileSample(
                    file=tracked.file,
                    timestamp=timestamp,
                    size_bytes=size,
                    **{name: getattr(counters, name) for name in COUNTER_FIELDS},
                )

            self._history.append(batch)

    def get_metrics(self, time_interval: int) -> dict[File, FileMetric | None]:
        if time_interval <= 0:
            raise ValueError("time interval must be positive")

        with self._lock:
            if len(self._history) > time_interval:
                latest_batch = self._history[-1]
                older_batch = self._history[-(time_interval + 1)]
            else:
                latest_batch = {}
                older_batch = {}

            result = {}
            for tracked in self._tracked.values():
                latest = latest_batch.get(tracked.file)
                older = older_batch.get(tracked.file)
                if latest is None or older is None:
                    result[tracked.file] = None
                else:
                    result[tracked.file] = self._make_metric(older, latest, time_interval)

        return result

    def _fetch_data_loop(self) -> None:
        next_sample = time.monotonic()

        while not self._stop_event.is_set():
            self.sample()
            next_sample += 1

            sleep_time = max(0, next_sample - time.monotonic())
            self._stop_event.wait(sleep_time)

    def _track_locked(self, file: File) -> File | ErrorCode:
        existing = self._tracked.get(file.absolute_path)
        if existing is not None:
            return existing.file

        stat_key = (file.device, file.inode)
        owner = self._stat_owners.get(stat_key)
        if owner is not None:
            return self._tracked[owner].file

        if not self._free_slots:
            return ErrorCode.TRACKING_LIMIT_REACHED

        slot = self._free_slots.pop()
        tracked = _TrackedFile(file=file, slot=slot)

        if self._probe is not None:
            self._probe.reset(slot)
            if not self._bind_locked(file.absolute_path, tracked):
                self._free_slots.append(slot)
                return ErrorCode.PERMISSION_DENIED

        self._tracked[file.absolute_path] = tracked
        self._stat_owners[stat_key] = file.absolute_path
        return file

    def _bind_locked(self, path: str, tracked: _TrackedFile) -> bool:
        key = self._probe.kernel_key(path)
        if key is None:
            return False
        if key == tracked.kernel_key:
            return True

        self._unbind_locked(path, tracked)
        self._kernel_owners[key] = path
        self._probe.add(tracked.slot, key)
        tracked.kernel_key = key
        return True

    def _unbind_locked(self, path: str, tracked: _TrackedFile) -> None:
        key = tracked.kernel_key
        tracked.kernel_key = None
        if key is not None and self._kernel_owners.get(key) == path:
            del self._kernel_owners[key]
            if self._probe is not None:
                self._probe.remove(key)

    def _release_locked(self, path: str, tracked: _TrackedFile) -> None:
        stat_key = (tracked.file.device, tracked.file.inode)
        if self._stat_owners.get(stat_key) == path:
            del self._stat_owners[stat_key]

        self._unbind_locked(path, tracked)
        if self._probe is not None:
            self._probe.reset(tracked.slot)
        self._free_slots.append(tracked.slot)

        for batch in self._history:
            batch.pop(tracked.file, None)

    def _refresh_locked(self) -> dict[str, int]:
        sizes = {}

        for path, tracked in self._tracked.items():
            try:
                st = os.stat(path)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue

            sizes[path] = st.st_size
            new_stat_key = (st.st_dev, st.st_ino)
            old_stat_key = (tracked.file.device, tracked.file.inode)

            if new_stat_key != old_stat_key:
                if self._stat_owners.get(old_stat_key) == path:
                    del self._stat_owners[old_stat_key]
                self._stat_owners[new_stat_key] = path
                tracked.file = File(absolute_path=path, inode=st.st_ino, device=st.st_dev)
                self._bind_locked(path, tracked)
            elif tracked.kernel_key is None:
                self._bind_locked(path, tracked)

        return sizes

    @staticmethod
    def _make_metric(older: FileSample, latest: FileSample, time_interval: int) -> FileMetric:
        def delta(name: str) -> int:
            return getattr(latest, name) - getattr(older, name)

        def average(sum_name: str, count_name: str) -> float | None:
            count = delta(count_name)
            return delta(sum_name) / count if count > 0 else None

        return FileMetric(
            file=latest.file,
            timestamp=older.timestamp,
            duration=time_interval,
            read_attempts=delta("read_attempts"),
            read_requested_bytes=delta("read_requested_bytes"),
            read_success_ops=delta("read_success_ops"),
            read_completed_bytes=delta("read_completed_bytes"),
            read_average_gap=average("read_gap_sum", "read_gap_count"),
            write_attempts=delta("write_attempts"),
            write_requested_bytes=delta("write_requested_bytes"),
            write_success_ops=delta("write_success_ops"),
            write_completed_bytes=delta("write_completed_bytes"),
            write_average_gap=average("write_gap_sum", "write_gap_count"),
        )
