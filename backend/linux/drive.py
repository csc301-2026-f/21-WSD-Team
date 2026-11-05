# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from datetime import datetime, timezone
import subprocess
import json
import shutil

from .models import Drive, DriveSample, Partition
from .constants import *


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


def _get_all_partition(drive_name: str) -> list[str]:

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


def _get_partition_storage(partition_name: str) -> tuple[int, int]:
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
        for partition_name in _get_all_partition(name):
            total, available = _get_partition_storage(partition_name)
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


def sample_all_drive(drives: tuple[str, ...]) -> tuple[DriveSample, ...]:
    wanted = set(drives)

    with open("/proc/diskstats", encoding="utf-8") as f:
        lines = f.readlines()

    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    samples = []

    for line in lines:
        fields = line.split()
        if len(fields) < DISKSTATS_MIN_FIELDS or fields[DISKSTATS_DEVICE_ID_INDEX] not in wanted:
            continue

        samples.append(DriveSample(
            device_id=fields[DISKSTATS_DEVICE_ID_INDEX],
            timestamp=timestamp,
            sectors_read=int(fields[DISKSTATS_SECTORS_READ_INDEX]),
            sectors_write=int(fields[DISKSTATS_SECTORS_WRITE_INDEX]),
            reads_complete=int(fields[DISKSTATS_READS_COMPLETE_INDEX]),
            writes_complete=int(fields[DISKSTATS_WRITES_COMPLETE_INDEX]),
        ))

    return tuple(samples)
