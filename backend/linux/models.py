from dataclasses import dataclass


@dataclass(frozen=True)
class Drive:
    device_id: str
    model: str
    serial: str
    size_bytes: int
    free_bytes: int
    is_available: bool
    media_type: str


@dataclass(frozen=True)
class Process:
    pid: int
    name: str
    start_time_timestamp: str


@dataclass(frozen=True)
class DriveMetric:
    timestamp: str
    duration: float
    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int


@dataclass(frozen=True)
class ProcessMetric:
    timestamp: str
    duration: float
    read_bytes: int
    write_bytes: int
    reads_complete: int
    writes_complete: int

@dataclass(frozen=True)
class DriveSample:
    device_id: str
    timestamp: str
    sectors_read: int
    sectors_write: int
    reads_complete: int
    writes_complete: int


@dataclass(frozen=True)
class ProcessSample:
    pid: str
    timestamp: str
    sectors_read: int
    sectors_write: int
    reads_complete: int
    writes_complete: int
