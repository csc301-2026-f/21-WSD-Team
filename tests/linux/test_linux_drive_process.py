# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only

import json
import os
import subprocess
import time

import pytest

from backend.linux import drive, process
from backend.linux.collector import DiskIOCollector, ProcessIOCollector
from backend.linux.models import Drive, DriveMetric, ErrorCode, ProcessMetric

# Sample lsblk -Jdb -o NAME,TRAN,MODEL,SERIAL,SIZE output: one HDD, one NVMe
# SSD, one USB stick, plus devices that must be ignored (loop, zram, cdrom).
LSBLK_DRIVES = {
    "blockdevices": [
        {"name": "sda", "tran": "sata", "model": "ST2000DM008", "serial": "ZFL1",
         "size": 2000398934016},
        {"name": "nvme0n1", "tran": "nvme", "model": "Samsung SSD 980",
         "serial": "S64D", "size": 1000204886016},
        {"name": "sdb", "tran": "usb", "model": None, "serial": None,
         "size": 31008735232},
        {"name": "loop0", "tran": None, "model": None, "serial": None,
         "size": 4096},
        {"name": "zram0", "tran": None, "model": None, "serial": None,
         "size": 8589934592},
        {"name": "sr0", "tran": "ata", "model": "DVD", "serial": "X",
         "size": 1073741312},
    ]
}

LSBLK_PARTITIONS = {
    "sda": {"blockdevices": [{"name": "sda", "type": "disk", "children": [
        {"name": "sda1", "type": "part"},
        {"name": "sda2", "type": "part", "children": [
            {"name": "luks-root", "type": "crypt"}]},
    ]}]},
    "nvme0n1": {"blockdevices": [{"name": "nvme0n1", "type": "disk", "children": [
        {"name": "nvme0n1p1", "type": "part"}]}]},
    "sdb": {"blockdevices": [{"name": "sdb", "type": "disk"}]},
}


def _fake_lsblk(args, text=True):
    if "-Jdb" in args:
        return json.dumps(LSBLK_DRIVES)
    if "NAME,TYPE" in args:
        name = args[-1].removeprefix("/dev/")
        return json.dumps(LSBLK_PARTITIONS[name])
    raise AssertionError(f"unexpected lsblk call: {args}")


@pytest.fixture
def fake_lsblk(monkeypatch):
    monkeypatch.setattr(drive.subprocess, "check_output", _fake_lsblk)
    monkeypatch.setattr(drive, "_get_partition_storage", lambda name: (100, 40))
    media = {"sda": "HDD", "nvme0n1": "SSD", "sdb": "SSD"}
    monkeypatch.setattr(drive, "_get_media_type", lambda name: media[name])


# --------------------------------------------------------------------------- #
# Drive detection
# --------------------------------------------------------------------------- #
def test_only_physical_drives_are_listed(fake_lsblk):
    names = [d.device_id for d in drive.get_all_drive()]
    assert names == ["sda", "nvme0n1", "sdb"]


def test_drive_fields_are_filled(fake_lsblk):
    hdd, ssd, usb = drive.get_all_drive()
    assert (hdd.model, hdd.serial, hdd.size_bytes, hdd.media_type) == \
        ("ST2000DM008", "ZFL1", 2000398934016, "HDD")
    assert ssd.media_type == "SSD"
    assert usb.model == "Unknown Model"
    assert usb.serial == "N/A"
    assert hdd.timestamp.endswith("Z")


def test_partitions_are_found_including_nested(fake_lsblk):
    hdd, ssd, usb = drive.get_all_drive()
    assert [p.name for p in hdd.partitions] == ["sda1", "sda2"]
    assert [p.name for p in ssd.partitions] == ["nvme0n1p1"]
    assert usb.partitions == ()
    assert (hdd.partitions[0].size_bytes, hdd.partitions[0].available_bytes) == (100, 40)


def test_missing_lsblk_gives_empty_list(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("lsblk")
    monkeypatch.setattr(drive.subprocess, "check_output", missing)
    assert drive.get_all_drive() == []


def test_broken_lsblk_output_gives_empty_list(monkeypatch):
    monkeypatch.setattr(drive.subprocess, "check_output", lambda *a, **k: "not json")
    assert drive.get_all_drive() == []


def test_failing_lsblk_gives_empty_list(monkeypatch):
    def fails(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "lsblk")
    monkeypatch.setattr(drive.subprocess, "check_output", fails)
    assert drive.get_all_drive() == []


def test_unknown_device_media_type_is_unknown():
    assert drive._get_media_type("wsd-no-such-device") == "Unknown"


# --------------------------------------------------------------------------- #
# Disk sampling (real /proc/diskstats)
# --------------------------------------------------------------------------- #
def _first_real_disk():
    with open("/proc/diskstats", encoding="utf-8") as f:
        for line in f:
            fields = line.split()
            if len(fields) >= 14:
                return fields[2]
    pytest.skip("no disks listed in /proc/diskstats")


def test_sample_all_drive_reads_real_counters():
    name = _first_real_disk()
    samples = drive.sample_all_drive((name,))
    assert [s.device_id for s in samples] == [name]
    assert samples[0].sectors_read >= 0 and samples[0].writes_complete >= 0


def test_sample_all_drive_ignores_unknown_devices():
    assert drive.sample_all_drive(("wsd-no-such-device",)) == ()


def _drive(name):
    return Drive(timestamp="2026-01-01T00:00:00Z", device_id=name, model="m",
                 serial="s", size_bytes=1, media_type="SSD", partitions=())


def test_disk_collector_rejects_unknown_device_and_short_history():
    name = _first_real_disk()
    collector = DiskIOCollector((_drive(name),))
    # No metric is produced (the error value is None today; may become an ErrorCode)
    assert not isinstance(collector.get_metric(1, "wsd-no-such-device"), DriveMetric)
    assert not isinstance(collector.get_metric(1, name), DriveMetric)  # no samples yet
    assert not isinstance(collector.get_metric(0, name), DriveMetric)


def test_disk_collector_produces_metric_after_two_samples():
    name = _first_real_disk()
    collector = DiskIOCollector((_drive(name),))
    collector.start()
    try:
        time.sleep(2.3)
        metric = collector.get_metric(1, name)
    finally:
        collector.stop()
    assert isinstance(metric, DriveMetric), metric
    assert metric.duration == 1
    assert metric.read_bytes >= 0 and metric.write_bytes >= 0


# --------------------------------------------------------------------------- #
# Processes (real /proc)
# --------------------------------------------------------------------------- #
def _own_name():
    with open(f"/proc/{os.getpid()}/comm", encoding="utf-8") as f:
        return f.read().strip()


def test_current_process_is_listed():
    pids = {p.pid for p in process.get_all_process()}
    assert os.getpid() in pids


def test_process_from_pid_has_name_and_start_time():
    me = process.get_process_from_pid(os.getpid())
    assert me is not None
    assert me.name == _own_name()
    assert me.start_time_timestamp


def test_unknown_pid_gives_none():
    with open("/proc/sys/kernel/pid_max", encoding="utf-8") as f:
        pid_max = int(f.read())
    assert process.get_process_from_pid(pid_max + 1) is None


def test_process_sample_reads_own_io_counters():
    me = process.get_process_from_pid(os.getpid())
    sample = process._sample_process_io(me)
    assert sample is not None
    assert sample.read_bytes >= 0 and sample.writes_complete >= 0


def test_process_collector_short_history_and_unknown_pid():
    collector = ProcessIOCollector()
    assert collector.get_metric(1, os.getpid()) == ErrorCode.INVALID_TIME_INTERVAL


def test_process_collector_produces_metric_for_own_process():
    collector = ProcessIOCollector()
    collector.start()
    try:
        time.sleep(2.3)
        metric = collector.get_metric(1, os.getpid())
        missing = collector.get_metric(1, 999_999_999)
    finally:
        collector.stop()
    assert isinstance(metric, ProcessMetric), metric
    assert metric.read_bytes >= 0 and metric.write_bytes >= 0
    assert missing == ErrorCode.PROCESS_NOT_FOUND
