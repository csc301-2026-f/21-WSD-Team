#data records as proposed in 02.1
from dataclasses import dataclass
from typing import Literal


MediaType = Literal["hdd", "ssd", "unknown"]


@dataclass(frozen=True)
class Device:
    host_id: str
    device_id: str
    display_name: str
    media_type: MediaType | None
    capacity_bytes: int | None
    free_bytes: int | None
    mount_points: list[str]
    is_available: bool


@dataclass(frozen=True)
class DeviceMetric:
    host_id: str
    device_id: str
    timestamp_utc: str
    sample_window_seconds: float

    read_bytes_per_sec: float | None
    write_bytes_per_sec: float | None
    read_iops: float | None
    write_iops: float | None
    avg_read_latency_ms: float | None
    avg_write_latency_ms: float | None

    source: str


@dataclass(frozen=True)
class ProcessMetric:
    host_id: str
    pid: int
    start_time_utc: str | None
    process_name: str | None
    timestamp_utc: str
    sample_window_seconds: float

    read_bytes_per_sec: float | None
    write_bytes_per_sec: float | None
    attributed_device_id: str | None


@dataclass(frozen=True)
class FileActivity:
    # Only emit this model when file-level attribution is verified.
    host_id: str
    file_id: str | None
    path: str | None
    device_id: str | None

    window_start_utc: str
    window_end_utc: str

    read_bytes: int | None
    write_bytes: int | None
    read_ops: int | None
    write_ops: int | None
    file_size_bytes: int | None

    source: str


@dataclass(frozen=True)
class RawIoEvent:
    """Internal normalized event; never expose directly to CORE."""

    timestamp_ns: int
    operation: str  # "read" or "write"

    pid: int | None
    process_start_time_utc: str | None
    process_name: str | None

    device_id: str | None
    transferred_bytes: int | None
    duration_ns: int | None

    file_id: str | None = None
    path: str | None = None
    file_size_bytes: int | None = None

    # True only when file identity/path correlation was validated.
    file_attribution_verified: bool = False

    # The decoder should emit one event per completed logical I/O.
    source: str = "windows_etw"


@dataclass(frozen=True)
class CollectionHealth:
    running: bool
    events_received: int
    events_lost: int
    last_event_utc: str | None
    last_error: str | None
