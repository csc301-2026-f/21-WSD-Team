# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from dataclasses import asdict
from datetime import datetime, timedelta
import os

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

def normalize_windows_file_activity(activities) -> list[dict]:
    normalized_file_activity = []
    for activity in activities:
        file_activity_dict = asdict(activity)
        if file_activity_dict["file_id"] is not None:
            file_activity_dict["file_id"] = str(file_activity_dict["file_id"])
        if file_activity_dict["device_id"] is not None:
            file_activity_dict["device_id"] = str(file_activity_dict["device_id"])
        normalized_file_activity.append(file_activity_dict)
    return normalized_file_activity

def normalize_windows_collection_health(collection):
    #Not in D2 requirement
    pass

def normalize_linux_device(devices, host_id) -> list[dict]:
    normalized_devices = []
    for device in devices:
        free_bytes = 0
        mount_points = []
        for partition in device.partitions:
            free_bytes += partition.available_bytes
            if partition.mount_point:
                mount_points.append(partition.mount_point)
        device_dict = {"host_id": host_id,
                       "device_id": device.device_id,
                       "display_name": device.model,
                       "media_type": device.media_type.lower(),
                       "capacity_bytes": device.size_bytes,
                       "free_bytes": free_bytes,
                       "mount_points": mount_points,
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
                       "sample_window_seconds": float(metric.duration),
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
            "sample_window_seconds": float(metric.duration),
            "read_bytes_per_sec": metric.read_bytes / metric.duration,
            "write_bytes_per_sec": metric.write_bytes / metric.duration,
            "attributed_device_id": None} #TODO data not provide
        normalized_process_matric.append(metric_dict)
    return normalized_process_matric

def normalize_linux_file_activity(file_stats, host_id) -> list[dict]:
    #TODO not yet decided
    normalized_file_io = []
    for file in file_stats:
        file_matric = file_stats[file]
        if file_matric is not None:
            start_time = datetime.fromisoformat(file_matric.timestamp.replace("Z", "+00:00"))
            end_time = start_time + timedelta(seconds = file_matric.duration)
            end_utc = end_time.isoformat().replace("+00:00", "Z")
            try:
                file_size = os.stat(file_matric.file.absolute_path).st_size
            except OSError:
                file_size = None
            metric_dict = {"host_id": host_id,
                           "file_id": str(file_matric.file.file_id),
                           "path": file_matric.file.absolute_path,
                           "device_id": file_matric.file.device,
                           "window_start_utc": file_matric.timestamp,
                           "window_end_utc": end_utc,
                           "read_bytes": file_matric.read_completed_bytes,
                           "write_bytes": file_matric.write_completed_bytes,
                           "read_ops": file_matric.read_success_ops,
                           "write_ops": file_matric.write_success_ops,
                           "read_average_gap": file_matric.read_average_gap,
                           "write_average_gap": file_matric.write_average_gap,
                           "file_size_bytes": file_size, #TODO data not provide, using the suggestion
                           "source": "linux_ebpf" #suggested by contract
                           }
            normalized_file_io.append(metric_dict)
    return normalized_file_io