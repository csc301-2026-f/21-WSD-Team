from datetime import datetime, timezone
import subprocess
from .models import Drive, DriveSample, Process, ProcessSample, ProcessMetric
import json
import shutil
import os
import time

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


def _sample_drive_io(
    drive_name: str,
) -> DriveSample:
    """
    Sample the current IO stats for target drive

    :param drive_name: id of drive, can be obtained using lsblk
    :return: a DriveSample object
    """

    output = subprocess.check_output(["cat", "/proc/diskstats"], text=True)

    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 10 and fields[2] == drive_name:
            return DriveSample(
                device_id=drive_name,
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),                sectors_read=int(fields[5]),
                sectors_write=int(fields[9]),
                reads_complete=int(fields[3]),
                writes_complete=int(fields[7]),
            )

    raise RuntimeError(f"Drive '{drive_name}' not found in /proc/diskstats")


def sample_all_drive(
        drives: tuple[str, ...]
) -> tuple[DriveSample]:
    samples = []
    for drive in drives:
        samples.append(_sample_drive_io(drive))
    return tuple(samples)


def _is_drive_available(drive_name: str) -> bool:

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

    return False


def _get_drive_available_space(drive_name: str) -> int:
    try:
        output = subprocess.check_output(
            ["lsblk", "-rn", "-o", "MOUNTPOINTS", f"/dev/{drive_name}"],
            text=True
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return 0

    for line in output.splitlines():
        mount_point = line.strip()
        if mount_point:
            try:
                usage = shutil.disk_usage(mount_point)
                return usage.free
            except OSError:
                continue

    return 0


def get_all_drive() -> list[Drive]:
    """
    Returns a tuple with name of all physical drives currently mounted

    :return: a tuple of all physical drive names

    example return: (nvme0n1, nvme1n1, sda, sdb)
    """
    try:
        # -J requests JSON format, -d excludes partitions, -n hides headers, -o specifies columns
        output = subprocess.check_output(
            ["lsblk", "-Jdnro", "NAME,TRAN,MODEL,SERIAL,SIZE"], text=True
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    try:
        data = json.loads(output)
        blockdevices = data.get("blockdevices", [])
    except json.JSONDecodeError:
        return []

    drives = []
    for dev in blockdevices:
        name = dev.get("name")
        tran = dev.get("tran") or ""
        model = dev.get("model") or "Unknown Model"
        serial = dev.get("serial") or "N/A"
        size = int(dev.get("size") or "0") * 512
        available_space = _get_drive_available_space(name)
        is_available = _is_drive_available(name)
        media_type = _get_media_type(name)

        # Filter for physical transports
        if tran in ("sata", "nvme", "usb", "sas", "scsi", "mmc"):
            drives.append(Drive(name, model, serial, size, available_space, is_available, media_type))

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

    #TODO: permission
    proc_path = f"/proc/{pid}"

    if not os.path.exists(proc_path):
        return None

    try:
        comm_path = os.path.join(proc_path, "comm")
        with open(comm_path, "r", encoding="utf-8") as f:
            name = f.read().strip()

        # 2. Extract start time from the /proc/[pid] directory stats (st_mtime)
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


def get_pid_open_file() -> tuple[str]:
    """
    Returns a tuple of all files opened by process PID

    :param pid: PID of target process
    :return: a tuple of all opened file by the target process

    example return: ("/home/xxx/program1", "/home/xxx/program2", "/mnt/smbshare/file1")
    """
    #TODO

    pass


def get_process_io(pid: int) -> ProcessMetric | None:
    def sample() -> dict[str, int]:
        output = subprocess.check_output(
            ["cat", f"/proc/{pid}/io"],
            text=True,
        )
        return {
            key: int(value)
            for key, value in (
                line.split(":") for line in output.splitlines()
            )
        }

    try:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        before = sample()

        time.sleep(1)

        after = sample()

        return ProcessMetric(
            timestamp=timestamp,
            duration=1,
            read_bytes=after["read_bytes"] - before["read_bytes"],
            write_bytes=after["write_bytes"] - before["write_bytes"],
            reads_complete=after["syscr"] - before["syscr"],
            writes_complete=after["syscw"] - before["syscw"]
        )

    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
        return None



if __name__ == "__main__":
    pass
