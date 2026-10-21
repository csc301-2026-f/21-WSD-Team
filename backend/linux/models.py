from dataclasses import dataclass


@dataclass(frozen=True)
class Partition:
    """
    Represents a partition on a physical storage device.

    Attributes:
        name: Linux partition identifier, such as "sda1" or "nvme0n1p1".
        size_bytes: Total filesystem storage capacity in bytes.
        available_bytes: Available filesystem storage in bytes.

    Note:
        For partitions without a mounted filesystem, storage information
        may be unavailable and the size fields may be zero.
    """
    name: str
    size_bytes: int
    available_bytes: int


@dataclass(frozen=True)
class Drive:
    """
    Represents a physical storage device detected by the Linux backend.

    Attributes:
        timestamp: UTC timestamp when the device information was collected,
            formatted as an ISO 8601 string.
        device_id: Linux block device name, such as "sda" or "nvme0n1".
        model: Hardware model reported by the operating system.
        serial: Hardware serial number, if available.
        size_bytes: Total capacity of the physical device in bytes.
        media_type: Storage media type, typically "SSD", "HDD", or "Unknown".
        partitions: Tuple containing the partitions detected on this device.

    Note:
        This model describes device information, not real-time I/O activity.
        Use DriveMetric for measured disk I/O over a sampling interval.
    """
    timestamp: str
    device_id: str
    model: str
    serial: str
    size_bytes: int
    media_type: str
    partitions: tuple[Partition, ...]


@dataclass(frozen=True)
class Process:
    """
    Represents a Linux process.

    Attributes:
        pid: Process identifier assigned by the operating system.
        name: Process name reported by Linux.
        start_time_timestamp: Timestamp intended to identify when the
            process started, formatted as an ISO 8601 string.

    Note:
        Linux may reuse PIDs after processes terminate. The start-time
        attribute is intended to help distinguish different processes
        that have the same PID.
    """
    pid: int
    name: str
    start_time_timestamp: str


@dataclass(frozen=True)
class DriveMetric:
    """
    Represents disk I/O activity measured over a sampling interval.

    Unlike DriveSample, which stores cumulative kernel counters,
    DriveMetric stores the differences between two samples.

    Attributes:
        timestamp: UTC timestamp of the beginning of the sampling interval.
        duration: Requested sampling interval in seconds.
        read_bytes: Total bytes read by the device during the interval.
        write_bytes: Total bytes written by the device during the interval.
        read_count: Number of completed read operations during the interval.
        write_count: Number of completed write operations during the interval.

    Note:
        These metrics are derived from Linux /proc/diskstats counters.
        Read/write byte values are calculated from sector counts.

        Duration currently reflects the requested interval rather than
        a precise measurement of elapsed wall-clock time.
    """
    timestamp: str
    duration: int
    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int


@dataclass(frozen=True)
class ProcessMetric:
    """
    Represents I/O activity attributed to a process over a sampling interval.

    The values are calculated by subtracting two cumulative ProcessSample
    measurements belonging to the same process.

    Attributes:
        timestamp: UTC timestamp of the beginning of the sampling interval.
        duration: Requested sampling interval in seconds.
        read_bytes: Bytes attributed to storage reads during the interval.
        write_bytes: Bytes attributed to storage writes during the interval.
        reads_complete: Number of read-related system calls during the interval.
        writes_complete: Number of write-related system calls during the interval.

    Note:
        Byte counters come from read_bytes and write_bytes in /proc/[pid]/io.
        These represent storage I/O accounting, not necessarily all bytes
        read or written through application-level APIs.

        The operation counters come from syscr and syscw in /proc/[pid]/io.
        They count read/write system calls rather than completed physical
        disk operations.

        Some processes cannot be sampled without additional permissions.
    """
    timestamp: str
    duration: int
    read_bytes: int
    write_bytes: int
    reads_complete: int
    writes_complete: int


@dataclass(frozen=True)
class DriveSample:
    """
    Represents a snapshot of cumulative disk I/O counters.

    Values are collected from Linux /proc/diskstats. Counters generally
    increase as the device performs I/O and are not reset after each sample.

    Attributes:
        device_id: Linux block device name associated with this sample.
        timestamp: UTC timestamp when the sample was collected.
        sectors_read: Cumulative number of sectors read.
        sectors_write: Cumulative number of sectors written.
        reads_complete: Cumulative number of completed read operations.
        writes_complete: Cumulative number of completed write operations.

    Note:
        Linux diskstats reports sectors in units of 512 bytes.
        To calculate bytes transferred between two samples:

            read_bytes = (new.sectors_read - old.sectors_read) * 512

        DriveSample is intended for internal collection and history.
        DriveMetric represents the activity within a selected interval.
    """
    device_id: str
    timestamp: str
    sectors_read: int
    sectors_write: int
    reads_complete: int
    writes_complete: int


@dataclass(frozen=True)
class ProcessSample:
    """
    Represents a snapshot of cumulative I/O counters for one process.

    Values are collected from Linux /proc/[pid]/io and represent
    cumulative activity attributed to the process.

    Attributes:
        process: Process object identifying the process being sampled.
        timestamp: UTC timestamp when the sample was collected.
        read_bytes: Cumulative bytes attributed to storage reads.
        write_bytes: Cumulative bytes attributed to storage writes.
        reads_complete: Cumulative count of read-related system calls.
        writes_complete: Cumulative count of write-related system calls.

    Note:
        The counters are cumulative, not per-second values.

        Subtracting an older ProcessSample from a newer ProcessSample
        for the same process produces the values in ProcessMetric.

        The Process identity should be checked before calculating
        differences because Linux can reuse process IDs.
    """
    process: Process
    timestamp: str
    read_bytes: int
    write_bytes: int
    reads_complete: int
    writes_complete: int