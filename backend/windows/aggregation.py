
from collections import deque
from datetime import datetime, timezone
from threading import Lock
import time

from .contracts import (
    DeviceMetric,
    ProcessMetric,
    RawIoEvent,
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
        events = self._snapshot(start_ns, end_ns)

        results = []

        for device_id in device_ids:
            selected = [
                e for e in events if e.device_id == device_id
            ] #manually sort the events per device when asked
            reads = [e for e in selected if e.operation == "read"]
            writes = [e for e in selected if e.operation == "write"]

            def byte_total(items: list[RawIoEvent]) -> int | None:
                if not items or any(
                    e.transferred_bytes is None for e in items
                ):
                    return None #means unavailable, something went wrong
                return sum(e.transferred_bytes for e in items)

            def average_latency(
                items: list[RawIoEvent],
            ) -> float | None:
                durations = [
                    e.duration_ns for e in items
                    if e.duration_ns is not None
                ]
                if not durations:
                    return None
                return sum(durations) / len(durations) / 1_000_000

            read_bytes = byte_total(reads)
            write_bytes = byte_total(writes)

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
                avg_read_latency_ms=average_latency(reads),
                avg_write_latency_ms=average_latency(writes),
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

        process_keys = {
            (e.pid, e.process_start_time_utc)
            for e in events if e.pid is not None
        }
        results = []

        for pid, process_start in process_keys:
            selected = [
                e for e in events
                if e.pid == pid
                and e.process_start_time_utc == process_start
            ]
            reads = [e for e in selected if e.operation == "read"]
            writes = [e for e in selected if e.operation == "write"]

            devices = {
                e.device_id for e in selected
                if e.device_id is not None
            }

            def rate(items: list[RawIoEvent]) -> float | None:
                if not items or any(
                    e.transferred_bytes is None for e in items
                ):
                    return None #if there's a None somewhere, it's contagious
                return sum(
                    e.transferred_bytes for e in items
                ) / sample_window_seconds

            results.append(ProcessMetric(
                host_id=self.host_id,
                pid=pid,
                start_time_utc=process_start,
                process_name=next(
                    (e.process_name for e in reversed(selected)
                     if e.process_name),
                    None,
                ),
                timestamp_utc=utc_timestamp(end_ns),
                sample_window_seconds=sample_window_seconds,
                read_bytes_per_sec=rate(reads),
                write_bytes_per_sec=rate(writes),
                attributed_device_id=(
                    next(iter(devices)) if len(devices) == 1 else None
                ),
            ))

        return results
