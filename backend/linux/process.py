from datetime import datetime, timezone
import os

from .models import Process, ProcessSample
from .constants import *


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


def _get_pid_tick(pid: int) -> int:
    proc_path = f"/proc/{pid}/stat"
    with open(proc_path, "r") as f:
        content = f.read()

    fields = content[content.rfind(")") + STARTING_INDEX_SINCE_BRACKET:].split()

    return int(fields[PROCESS_START_TIME_INDEX])


def _get_system_boot_time() -> int:
    with open("/proc/stat", "r") as f:
        for line in f:
            if line.startswith("btime "):
                return int(line.split()[1])
        else:
            raise ValueError("Boot time not found")


def _get_pid_start_time(pid: int) -> str:

    tick_since_boot = _get_pid_tick(pid)
    tick_per_second = os.sysconf("SC_CLK_TCK")
    start_time = tick_since_boot / tick_per_second + _get_system_boot_time()
    formatted_time = datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    return formatted_time


def _get_process_info(pid: int) -> Process | None:

    proc_path = f"/proc/{pid}"

    if not os.path.exists(proc_path):
        return None

    try:
        comm_path = os.path.join(proc_path, "comm")
        with open(comm_path, "r", encoding="utf-8") as f:
            name = f.read().strip()

        return Process(
            pid=pid,
            name=name,
            start_time_timestamp=_get_pid_start_time(pid)
        )
    except (PermissionError, FileNotFoundError, OSError, ValueError):
        return None


def _sample_process_io(process: Process) -> ProcessSample | None:
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


def sample_all_process() -> dict[Process, ProcessSample]:
    processes = get_all_process()

    processes_io = {}
    for process in processes:
        sample = _sample_process_io(process)
        if sample is not None:
            processes_io[process] = sample

    return processes_io


def get_process_from_pid(pid: int) -> Process | None:
    for process in get_all_process():
        if process.pid == pid:
            return process
    return None
