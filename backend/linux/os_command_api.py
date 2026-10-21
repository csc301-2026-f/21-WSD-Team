from datetime import datetime, timezone
import subprocess
import json
import shutil
import os

from .models import Drive, DriveSample, Process, ProcessSample, Partition


def _get_media_type(
        device_name: str
) -> str:
    """

    :param device_name: id of drive, can be obtained using lsblk
    :return: a string that's either "HDD" or "SSD"
    """

    rotational_path = f"/sys/class/block/{device_name}/queue/rotational"

    try:
        with open(rotational_path, "r", encoding="utf-8") as f:
            value = f.read().strip()
            if value == "0":
                return "SSD"
            else:
                return "HDD"
    except (OSError, ValueError):
        return "Unknown"


def sample_all_drive(drives: tuple[str, ...]) -> tuple[DriveSample, ...]:
    wanted = set(drives)

    with open("/proc/diskstats", encoding="utf-8") as f:
        lines = f.readlines()

    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    samples = []

    for line in lines:
        fields = line.split()
        if len(fields) < 10 or fields[2] not in wanted:
            continue

        samples.append(DriveSample(
            device_id=fields[2],
            timestamp=timestamp,
            sectors_read=int(fields[5]),
            sectors_write=int(fields[9]),
            reads_complete=int(fields[3]),
            writes_complete=int(fields[7]),
        ))

    return tuple(samples)


"""def _is_drive_available(drive_name: str) -> bool:

    sysfs_path = f"/sys/class/block/{drive_name}"

    if not os.path.exists(sysfs_path):
        return False

    size_file_path = os.path.join(sysfs_path, "size")
    try:
        if os.path.exists(size_file_path):
            with open(size_file_path, "r") as f:
                sectors = int(f.read().strip())
                return sectors > 0
    except (OSError, ValueError):
        return False

    return False"""


def get_all_partition(drive_name: str) -> list[str]:

    try:
        output = subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,TYPE", f"/dev/{drive_name}"],
            text=True
        )
        devices = json.loads(output).get("blockdevices", [])
    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
        return []

    partitions = []

    def traverse(disks):
        name = disks.get("name")

        if disks.get("type") == "part":
            partitions.append(name)

        for child in disks.get("children") or []:
            traverse(child)

    for device in devices:
        traverse(device)

    return partitions


def get_partition_storage(partition_name: str) -> tuple[int, int]:
    try:
        output = subprocess.check_output(
            ["lsblk", "-J", "-o", "MOUNTPOINTS", f"/dev/{partition_name}"],
            text=True
        )

        data = json.loads(output)

        for device in data.get("blockdevices", []):
            for mount_point in device.get("mountpoints") or []:
                if not mount_point:
                    continue
                usage = shutil.disk_usage(mount_point)
                return usage.total, usage.free

    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    return 0, 0


def get_all_drive() -> list[Drive]:
    """
    Returns a list of object Drive

    :return: a list of all physical drive
    """
    try:
        output = subprocess.check_output(
            ["lsblk", "-Jdb", "-o", "NAME,TRAN,MODEL,SERIAL,SIZE"],
            text=True
        )
        blockdevices = json.loads(output).get("blockdevices", [])
    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
        return []

    drives = []
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for dev in blockdevices:
        name = dev.get("name")
        tran = dev.get("tran") or ""

        if not name or tran not in ("sata", "nvme", "usb", "sas", "scsi", "mmc"):
            continue

        model = dev.get("model") or "Unknown Model"
        serial = dev.get("serial") or "N/A"
        size = int(dev.get("size") or 0)
        media_type = _get_media_type(name)

        partitions = []
        for partition_name in get_all_partition(name):
            total, available = get_partition_storage(partition_name)
            partitions.append(
                Partition(
                    name=partition_name,
                    size_bytes=total,
                    available_bytes=available
                )
            )

        drives.append(
            Drive(
                timestamp=timestamp,
                device_id=name,
                model=model,
                serial=serial,
                size_bytes=size,
                media_type=media_type,
                partitions=tuple(partitions)
            )
        )

    return drives


def _get_all_pid() -> tuple[int, ...]:
    """
    Returns every pid of currently running process

    :return: a tuple of pid

    example return: (1, 2, 3)
    """
    pids = []
    try:
        for entry in os.listdir("/proc"):
            if entry.isdigit():
                pids.append(int(entry))
    except (FileNotFoundError, PermissionError):
        return ()

    return tuple(sorted(pids))


def _get_process_info(pid: int) -> Process | None:

    proc_path = f"/proc/{pid}"

    if not os.path.exists(proc_path):
        return None

    try:
        comm_path = os.path.join(proc_path, "comm")
        with open(comm_path, "r", encoding="utf-8") as f:
            name = f.read().strip()

        stat_info = os.stat(proc_path)
        dt = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc)
        start_time_timestamp = dt.isoformat().replace("+00:00", "Z")
        return Process(
            pid=pid,
            name=name,
            start_time_timestamp=start_time_timestamp
        )
    except (PermissionError, FileNotFoundError, OSError, ValueError):
        return None


def get_all_process() -> list[Process]:
    """
    Returns all running processes as Process objects.

    :return: a list of Process objects, each representing a process
    """
    processes = []
    for pid in _get_all_pid():
        proc = _get_process_info(pid)
        if proc:
            processes.append(proc)

    return processes


def sample_process_io(process: Process) -> ProcessSample | None:
    try:
        with open(f"/proc/{process.pid}/io") as f:
            data = {
                key.strip(): int(value.strip())
                for key, value in (
                    line.split(":", 1) for line in f
                )
            }

        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return ProcessSample(
            process=process,
            timestamp=timestamp,
            read_bytes=data["read_bytes"],
            write_bytes=data["write_bytes"],
            reads_complete=data["syscr"],
            writes_complete=data["syscw"],
        )

    except (OSError, ValueError, KeyError):
        return None


def sample_all_process() -> dict[Process, ProcessSample]:
    processes = get_all_process()

    processes_io = {}
    for process in processes:
        sample = sample_process_io(process)
        if sample is not None:
            processes_io[process] = sample

    return processes_io


def get_process_from_pid(pid: int) -> Process | None:
    for process in get_all_process():
        if process.pid == pid:
            return process
    return None


if __name__ == "__main__":
    pass
