# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from collections import deque
from datetime import datetime, timezone
from genericpath import getsize
from threading import Lock
from dataclasses import replace
import time

from .contracts import (
    DeviceMetric,
    ProcessMetric,
    RawIoEvent,
    FileActivity,
)


def utc_timestamp(timestamp_ns: int) -> str:
    seconds, nanos = divmod(timestamp_ns, 1_000_000_000)
    dt = datetime.fromtimestamp(seconds, timezone.utc)
    return dt.replace(
        microsecond=nanos // 1_000
    ).isoformat(timespec="microseconds").replace("+00:00", "Z")


class EventAggregator:
    def __init__(
        self,
        host_id: str,
        retention_seconds: int = 3600,
        max_events: int = 500_000,
    ):
        self.host_id = host_id
        self.retention_ns = retention_seconds * 1_000_000_000
        self._events = deque(maxlen=max_events)
        self._max_events = max_events
        self._received_total = 0
        self._lock = Lock()

    def add_event(self, event: RawIoEvent) -> None:
        if event.operation not in ("read", "write"): #drop events that are not our IO
            return

        with self._lock: 
            self._events.append(event)
            self._received_total += 1
            self._prune_locked(time.time_ns())

    def _prune_locked(self, now_ns: int) -> None:
        cutoff = now_ns - self.retention_ns
        while self._events and self._events[0].timestamp_ns < cutoff:
            self._events.popleft() #let go of events that have gone stale for 6 minutes

    def _snapshot(
        self, start_ns: int, end_ns: int
    ) -> list[RawIoEvent]:
        with self._lock:
            self._prune_locked(time.time_ns())
            return [
                event for event in self._events
                if start_ns <= event.timestamp_ns <= end_ns
            ]

    def device_metrics(
        self,
        device_ids: list[str],
        sample_window_seconds: float,
        now_ns: int | None = None,
    ) -> list[DeviceMetric]:
        if sample_window_seconds <= 0:
            raise ValueError("Sample window must be positive")

        end_ns = now_ns if now_ns is not None else time.time_ns()
        start_ns = end_ns - int(sample_window_seconds * 1e9)
        snapshot = self._snapshot(start_ns, end_ns)
        events = [e for e in snapshot if e.source == "diskIO"]

        results = []

        for device_id in device_ids:
            selected = [
                e for e in events if e.device_id == device_id
            ] #manually sort the events per device when asked
            reads = [e for e in selected if e.operation == "read"]
            writes = [e for e in selected if e.operation == "write"]
            #print(f"R/W in snapshot at time {end_ns} : {len(reads)}, {len(writes)}")

            read_bytes = self._byte_total(reads)
            write_bytes = self._byte_total(writes)

            results.append(DeviceMetric(
                host_id=self.host_id,
                device_id=device_id,
                timestamp_utc=utc_timestamp(end_ns),
                sample_window_seconds=sample_window_seconds,
                read_bytes_per_sec=(
                    read_bytes / sample_window_seconds
                    if read_bytes is not None else None
                ),
                write_bytes_per_sec=(
                    write_bytes / sample_window_seconds
                    if write_bytes is not None else None
                ),
                read_iops=len(reads) / sample_window_seconds,
                write_iops=len(writes) / sample_window_seconds,
                avg_read_latency_ms=self._average_latency(reads),
                avg_write_latency_ms=self._average_latency(writes),
                source="windows_etw",
            ))

        return results

    def process_metrics(
        self,
        sample_window_seconds: float,
        now_ns: int | None = None,
    ) -> list[ProcessMetric]:
        if sample_window_seconds <= 0:
            raise ValueError("Sample window must be positive")

        end_ns = now_ns if now_ns is not None else time.time_ns()
        start_ns = end_ns - int(sample_window_seconds * 1e9)
        events = self._snapshot(start_ns, end_ns)

        process_keys ={e.pid for e in events if e.pid is not None}
        results = []

        for pid in process_keys:
            if pid == 4294967295: continue #4294967295 is 0xFFFFFFFF, invalid
            selected = [
                e for e in events
                if e.pid == pid
                and e.source == "fileIO"
            ]
            reads = [e for e in selected if e.operation == "read"]
            writes = [e for e in selected if e.operation == "write"]

            devices = {
                e.device_id for e in selected
                if e.device_id is not None
            }

            results.append(ProcessMetric(
                host_id=self.host_id,
                pid=pid,
                start_time_utc=None,
                process_name=next(
                    (e.process_name for e in reversed(selected)
                     if e.process_name),
                    None,
                ),
                timestamp_utc=utc_timestamp(end_ns),
                sample_window_seconds=sample_window_seconds,
                read_bytes_per_sec=self._rate(reads,sample_window_seconds),
                write_bytes_per_sec=self._rate(writes,sample_window_seconds),
                attributed_device_id=(
                    next(iter(devices)) if len(devices) == 1 else None
                ),
            ))

        return results
    
    def file_activity(
            self,
            sample_window_seconds: float,
            now_ns: int | None = None,
        ) -> list[FileActivity]:
        if sample_window_seconds <= 0:
            raise ValueError("Sample window must be positive")
        
        end_ns = now_ns if now_ns is not None else time.time_ns()
        start_ns = end_ns - int(sample_window_seconds * 1e9)
        snapshot = self._snapshot(start_ns, end_ns)
        events = [e for e in snapshot if e.source == "fileIO"]
        results = []
        files = dict()
        #sort by letterless path, may lead to aliasing if two disks are set up the exact same way
        for e in events: files.setdefault(e.file_id,[]).append(e)
        if files is not None: 
            for file_id, file_events in files.items():
                if file_id is None: continue #malformed
                selected = file_events #all events pertaining to a given fileKey
                reads = [e for e in selected if e.operation == "read"]
                writes = [e for e in selected if e.operation == "write"]
                file_path = next((e.path for e in file_events if e.path is not None), None)
                disk_number = next((e.device_id for e in file_events if e.device_id is not None), None)
                path_letter = next((e.decoded_drive_letter for e in file_events if e.decoded_drive_letter is not None), None)
                if file_path is None or disk_number is None or path_letter is None: continue
                #we need at least one occurence of successful path decoding per fileID
                stripped_path = file_path.split('\\',3)[-1] #grab all after 3rd \
                absolute_path = path_letter + '\\' + stripped_path
                read_bytes = self._byte_total(reads)
                write_bytes = self._byte_total(writes)
                try: 
                    file_size = getsize(absolute_path)
                except:
                    file_size = None #e.g. file was deleted
                results.append(FileActivity(
                    host_id=self.host_id,
                    file_id=file_id,
                    path=absolute_path,
                    device_id=disk_number,
                    window_start_utc=utc_timestamp(start_ns),
                    window_end_utc=utc_timestamp(end_ns),
                    read_bytes=read_bytes,
                    write_bytes=write_bytes,
                    read_ops=len(reads),
                    write_ops=len(writes),
                    file_size_bytes=file_size,
                    source="windows_etw",
                    ))
        return self._combine_based_on_path(results)
        
    @staticmethod
    def _byte_total(items: list[RawIoEvent]) -> int | None:
        if not items or any(
            e.transferred_bytes is None for e in items
        ):
            return None #means unavailable, something went wrong
        return sum(e.transferred_bytes for e in items)
    
    @staticmethod
    def _average_latency(
        items: list[RawIoEvent],
    ) -> float | None:
        durations = [
            e.duration_ns for e in items
            if e.duration_ns is not None
            ]
        if not durations:
            return None
        return sum(durations) / len(durations) / 1_000_000

    @staticmethod
    def _rate(items: list[RawIoEvent], sample_window_seconds: float) -> float | None:
        if not items or any(
            e.transferred_bytes is None for e in items
        ):
            return None #if there's a None somewhere, it's contagious
        return sum(
            e.transferred_bytes for e in items
        ) / sample_window_seconds

    @staticmethod
    def _combine_based_on_path(metrics: list[FileActivity] | None) -> list[FileActivity] | None:
        """
        Combine FileActivity records with the same path, keeping the first file_id.
        Sum read_ops and write_ops, and add byte counts only when both values are not None.
        Otherwise, keep the existing byte count(or probably None).
        """
        file_dict = {}
        if metrics is not None:
            for metric in metrics:
                if metric.path is not None:
                    path = metric.path
                    if path not in file_dict:
                        file_dict[path] = metric
                    else:
                        new_read_bytes = file_dict[path].read_bytes
                        new_write_bytes = file_dict[path].write_bytes
                        if new_read_bytes is not None and metric.read_bytes is not None:
                            new_read_bytes += metric.read_bytes
                        if new_write_bytes is not None and metric.write_bytes is not None:
                            new_write_bytes += metric.write_bytes
                        new_read_ops = metric.read_ops + file_dict[path].read_ops
                        new_write_ops = metric.write_ops + file_dict[path].write_ops
                        file_dict[path] = replace(file_dict[path],
                                                  read_bytes = new_read_bytes,
                                                  write_bytes = new_write_bytes,
                                                  read_ops = new_read_ops,
                                                  write_ops = new_write_ops)
        return list(file_dict.values())