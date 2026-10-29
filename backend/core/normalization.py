# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from dataclasses import asdict


def size_to_bytes(size):
    if size is None:
        return None
    if size.endswith("G"):
        return int(float(size[:-1]) * 1024 ** 3)
    return None

def normalize_windows_device(devices) -> list[dict]:
    normalized_devices = []
    for device in devices:
        device_dict = asdict(device)
        device_dict["device_id"] = str(device_dict["device_id"])
        normalized_devices.append(device_dict)
    return normalized_devices

def normalize_windows_device_metric(metrics) -> list[dict]:
    normalized_device_metrics = []
    for metric in metrics:
        device_metric_dict = asdict(metric)
        device_metric_dict["device_id"] = str(device_metric_dict["device_id"])
        normalized_device_metrics.append(device_metric_dict)
    return normalized_device_metrics

def normalize_windows_process_metric(metrics) -> list[dict]:
    normalized_process_metrics = []
    for metric in metrics:
        process_metric_dict = asdict(metric)
        if process_metric_dict["attributed_device_id"] is not None:
            process_metric_dict["attributed_device_id"] = str(process_metric_dict["attributed_device_id"])
        normalized_process_metrics.append(process_metric_dict)
    return normalized_process_metrics

#TODO Found different in Windows backend
def normalize_windows_file_activity(activities) -> list[dict]:
    normalized_file_activity = []
    for activity in activities:
        file_activity_dict = asdict(activity)
        normalized_file_activity.append(file_activity_dict)
    return normalized_file_activity

def normalize_windows_collection_health(collection):
    #Not in D2 requirement
    pass

def normalize_linux_device(devices, host_id) -> list[dict]:
    normalized_devices = []
    for device in devices:
        free_bytes = 0
        for partition in device.partitions:
            free_bytes += partition.available_bytes
        device_dict = {"host_id": host_id,
                       "device_id": device.device_id,
                       "display_name": device.model,
                       "media_type": device.media_type.lower(),
                       "capacity_bytes": device.size_bytes,
                       "free_bytes": free_bytes,
                       "mount_points": [], #TODO data not provide
                       "is_available": True} #TODO data not provide
        normalized_devices.append(device_dict)
    return normalized_devices

def normalize_linux_device_metric(metrics, host_id) -> list[dict]:
    normalized_device_matric = []
    for tup in metrics:
        metric = tup[1]
        metric_dict = {"host_id": host_id,
                       "device_id": tup[0],
                       "timestamp_utc": metric.timestamp,
                       "sample_window_seconds": metric.duration,
                       "read_bytes_per_sec": metric.read_bytes / metric.duration,
                       "write_bytes_per_sec": metric.write_bytes / metric.duration,
                       "read_iops": metric.read_count / metric.duration,
                       "write_iops": metric.write_count / metric.duration,
                       "avg_read_latency_ms": None, #TODO data not provide
                       "avg_write_latency_ms": None, #TODO data not provide
                       "source": "/proc/diskstats"}
        normalized_device_matric.append(metric_dict)
    return normalized_device_matric

def normalize_linux_process_metric(metrics, host_id) -> list[dict]:
    normalized_process_matric = []
    for tup in metrics:
        process = tup[0]
        metric = tup[1]
        metric_dict = {
            "host_id": host_id,
            "pid": process.pid,
            "start_time_utc": process.start_time_timestamp,
            "process_name": process.name,
            "timestamp_utc": metric.timestamp,
            "sample_window_seconds": metric.duration,
            "read_bytes_per_sec": metric.read_bytes / metric.duration,
            "write_bytes_per_sec": metric.write_bytes / metric.duration,
            "attributed_device_id": None} #TODO data not provide
        normalized_process_matric.append(metric_dict)
    return normalized_process_matric

def normalize_linux_file_activity():
    #TODO agent not done
    pass