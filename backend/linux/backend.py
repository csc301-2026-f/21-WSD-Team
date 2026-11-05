# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from .models import Drive, Process, DriveMetric, ProcessMetric, File, FileMetric, ErrorCode
from .collector import DiskIOCollector, ProcessIOCollector, FileIOCollector
from .file import list_folder_files

from .process import get_all_process
from .drive import get_all_drive


class LinuxBackend:
    def __init__(self, host_id: str):
        self.host_id = host_id

        self._started = False

        self.disk_collector = DiskIOCollector(tuple(self.list_devices()))
        self.process_collector = ProcessIOCollector()
        self.file_collector = FileIOCollector()

    def start(self) -> ErrorCode | None:
        """
        Start background disk, process and file I/O collection.

        Disk and process collection start even if file tracking cannot.

        :return: None on success, or ErrorCode.FILE_TRACER_UNAVAILABLE if the
                 eBPF file tracer could not be loaded. Things that could cause the error are: (missing BCC, kernel
                 headers, privileges or fentry support)
                 A return of ErrorCode still means dick_collector and process_collector started.
        """
        if self._started:
            return None

        self.disk_collector.start()
        self.process_collector.start()
        rtn = self.file_collector.start()

        self._started = True
        return rtn

    def close(self) -> None:
        """
        Stop background collection and wait for both threads to terminate.
        """
        if not self._started:
            return

        self.disk_collector.stop()
        self.process_collector.stop()
        self.file_collector.stop()

        self._started = False

    def refresh_disk_collect(self) -> None:
        """
        Rediscover physical drives and restart the disk collector.

        Previous disk sampling history is discarded.
        """
        if not self._started:
            return

        self.disk_collector.stop()
        self.disk_collector = DiskIOCollector(tuple(self.list_devices()))
        self.disk_collector.start()

    def list_devices(self) -> list[Drive]:
        """
        Retrieve physical storage devices detected by Linux.

        :return: List of Drive objects, or an empty list if none are found
        """
        return get_all_drive()

    def list_processes(self) -> list[Process]:
        """
        Retrieve currently running processes.

        :return: List of Process objects, or an empty list if the backend
                 is stopped
        """
        if not self._started:
            return []

        return get_all_process()

    def get_device_io(
        self, interval_seconds: int, device_name: str
    ) -> DriveMetric | None:
        """
        Retrieve disk I/O statistics from previously collected samples.
        Does not block while waiting for new samples.

        :param interval_seconds: Number of one-second sampling intervals to compare; must be positive
        :param device_name: Linux block device ID, e.g. "nvme0n1"
        :return: DriveMetric containing interval I/O statistics, or None if stopped, device is invalid,
                 or history is insufficient
        """
        if not self._started:
            return None

        return self.disk_collector.get_metric(interval_seconds, device_name)

    def get_process_io(
        self, interval_seconds: int, pid: int
    ) -> ProcessMetric | None:
        """
        Retrieve process I/O statistics from previously collected samples.
        Process must exist in both samples being compared.

        :param interval_seconds: Number of one-second sampling intervals to compare; must be positive
        :param pid: Linux process ID
        :return: ProcessMetric containing interval I/O statistics, or None if stopped, history is insufficient,
                 process is unavailable, or access is denied
        """
        if not self._started:
            return None

        rtn = self.process_collector.get_metric(interval_seconds, pid)
        if isinstance(rtn, ErrorCode):
            return None
        else:
            return rtn

    def track_file(self, file_path: str) -> ErrorCode | File:
        """
        Start tracking I/O on a regular file.

        Tracking an already tracked file returns the existing File. If the file is later replaced at the same path, for
        example by an editor saving through rename, it keeps its record and counters continue.

        :param file_path: Absolute path to a regular file; symlinks are resolved
        :return: File being tracked, or an ErrorCode: PATH_NOT_ABSOLUTE,
                 FILE_NOT_FOUND, NOT_A_REGULAR_FILE, PERMISSION_DENIED,
                 TRACKING_LIMIT_REACHED or FILE_TRACER_UNAVAILABLE
        """
        return self.file_collector.track(file_path)

    def track_folder(self, folder_path: str) -> ErrorCode | tuple[File, ...]:
        """
        Track every regular file currently under a folder recursively.

        This is a snapshot. Meaning files created later are not picked up. Files that cannot be tracked are skipped. If
        the tracking limit is reached, the files tracked so far are returned.

        :param folder_path: Absolute path to a folder
        :return: Files being tracked, or an ErrorCode: PATH_NOT_ABSOLUTE,
                 FILE_NOT_FOUND, NOT_A_DIRECTORY, PERMISSION_DENIED or
                 FILE_TRACER_UNAVAILABLE
        """
        paths = list_folder_files(folder_path)
        if isinstance(paths, ErrorCode):
            return paths

        return self.file_collector.track_many(paths)

    def untrack_file(self, file: File) -> ErrorCode | None:
        """
        Stop tracking a file.

        :param file: File returned by track_file or track_folder
        :return: None, or ErrorCode.FILE_NOT_TRACKED
        """
        return self.file_collector.untrack(file)

    def untrack_folder(self, files: tuple[File, ...]) -> ErrorCode | None:
        """
        Stop tracking several files, for example the result of track_folder.

        :param files: Files to stop tracking
        :return: None, or ErrorCode.FILE_NOT_TRACKED if any file was not tracked; the remaining files are still untracked
        """
        return self.file_collector.untrack_many(files)

    def list_tracked_files(self) -> tuple[File, ...]:
        """
        Find every file currently being tracked.

        :return: Tuple of tracked File objects
        """
        return self.file_collector.tracked_files()

    def get_all_file_stats(self, interval_seconds: int) -> dict[File, FileMetric | None]:
        """
        Retrieve file I/O statistics for every tracked file from previously collected samples. Does not block while
        waiting for new samples.

        :param interval_seconds: Number of one-second sampling intervals to compare; must be positive
        :return: Mapping of every tracked File to its FileMetric, or to None if history is insufficient
        (for example a file tracked less than interval_seconds ago). Empty if the backend is stopped.
        """
        if not self._started:
            return {}

        return self.file_collector.get_metrics(interval_seconds)


"""    def get_all_process_io(self, interval_seconds: int) -> list[ProcessMetric]:
        if not self._started:
            return None

    def get_all_drive_io(self, interval_seconds: int) -> list[DriveMetric]:
        if not self._started:
            return None"""

