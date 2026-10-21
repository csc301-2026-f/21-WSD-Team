from dataclasses import dataclass


@dataclass(frozen=True)
class Partition:
    name: str
    size_bytes: int
    available_bytes: int


@dataclass(frozen=True)
class Drive:
    timestamp: str
    device_id: str
    model: str
    serial: str
    size_bytes: int
    media_type: str
    partitions: tuple[Partition, ...]


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
    process: Process
    sectors_read: int
    sectors_write: int
    reads_complete: int
    writes_complete: int
