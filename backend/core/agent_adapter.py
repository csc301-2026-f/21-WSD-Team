# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from .normalization import (normalize_windows_device,
                            normalize_windows_device_metric,
                            normalize_windows_process_metric,
                            normalize_windows_file_activity,
                            normalize_linux_device,
                            normalize_linux_device_metric,
                            normalize_linux_process_metric,
                            normalize_linux_file_activity)
from backend.linux.models import ErrorCode
import logging
logger = logging.getLogger(__name__)


class WindowsAgentAdapter:
    def __init__(self, backend):
        self.backend = backend

    def start(self) -> None:
        self.backend.start()

    def get_devices(self) -> list[dict]:
        return normalize_windows_device(self.backend.get_devices())

    def get_device_metrics(self, sample_window_seconds = 10.0) -> list[dict]:
        return normalize_windows_device_metric(self.backend.get_device_metrics(sample_window_seconds))

    def get_process_metrics(self, sample_window_seconds = 10.0) -> list[dict]:
        return normalize_windows_process_metric(self.backend.get_process_metrics(sample_window_seconds))

    def get_file_activity(self, sample_window_seconds = 10, now_ns = None) -> list[dict]:
        return normalize_windows_file_activity(self.backend.get_file_activity(sample_window_seconds, now_ns))

    def close(self):
        self.backend.close()


class LinuxAgentAdapter:
    def __init__(self, backend):
        self.backend = backend

    def start(self) -> None:
        start = self.backend.start()
        if start == ErrorCode.FILE_TRACER_UNAVAILABLE:
            logger.error("Linux FileIO service is unavailable")

    def get_devices(self) -> list[dict]:
        return normalize_linux_device(self.backend.list_devices(), self.backend.host_id)

    def get_device_metrics(self, sample_window_seconds = 1) -> list[dict]:
        devices = self.backend.list_devices()
        device_metric = []
        for device in devices:
            device_id = device.device_id
            metric = self.backend.get_device_io(sample_window_seconds, device_id)
            if isinstance(metric, ErrorCode):
                if metric == ErrorCode.BACKEND_NOT_STARTED:
                    logger.error("Backend not started")
                    raise RuntimeError("Backend not started")
                if metric == ErrorCode.INVALID_TIME_INTERVAL:
                    continue
                logger.error(f"Device error: {metric.name}")
                raise RuntimeError(f"Device error: {metric.name}")
            if metric is not None:
                device_metric.append((device_id, metric))
        return normalize_linux_device_metric(device_metric, self.backend.host_id)

    def get_process_metrics(self, sample_window_seconds = 1) -> list[dict]:
        processes = self.backend.list_processes()
        process_metric = []
        for process in processes:
            pid = process.pid
            metric = self.backend.get_process_io(sample_window_seconds, pid)
            if isinstance(metric, ErrorCode):
                if metric == ErrorCode.BACKEND_NOT_STARTED:
                    logger.error("Backend not started")
                    raise RuntimeError("Backend not started")
                if metric in (ErrorCode.INVALID_TIME_INTERVAL, ErrorCode.PROCESS_NOT_FOUND, ErrorCode.PROCESS_PID_REUSED):
                    continue
                logger.error(f"Process error: {metric.name}")
                raise RuntimeError(f"Process error: {metric.name}")
            if metric is not None:
                process_metric.append((process, metric))
        return normalize_linux_process_metric(process_metric, self.backend.host_id)

    def get_file_activity(self, sample_window_seconds = 10, now_ns = None) -> list[dict]:
        return normalize_linux_file_activity(self.backend.get_all_file_stats(sample_window_seconds), self.backend.host_id)

    def track_file(self, path):
        return self.backend.track_file(path)

    def track_folder(self, path):
        return self.backend.track_folder(path)

    def list_tracked_files(self):
        return self.backend.list_tracked_files()

    def untrack_file(self, file):
        return self.backend.untrack_file(file)

    def untrack_folder(self, files):
        return self.backend.untrack_folder(files)

    def close(self):
        self.backend.close()