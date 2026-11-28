# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import os
import subprocess
import threading
from typing import Callable

from .models import ErrorCode
from .constants import *


def validate_tracking_path(path: str) -> ErrorCode | None:
    """Validate a caller-supplied Linux path before filesystem access."""
    if not isinstance(path, str):
        return ErrorCode.INVALID_PATH
    try:
        os.fsencode(path)
    except UnicodeEncodeError:
        return ErrorCode.INVALID_PATH
    if not os.path.isabs(path):
        return ErrorCode.PATH_NOT_ABSOLUTE
    if any(ord(ch) < 32 or ord(ch) == 127 or ch in ";&|`<>" for ch in path):
        return ErrorCode.INVALID_PATH
    if "$(" in path or "${" in path:
        return ErrorCode.INVALID_PATH
    return None


def resolve_mergerfs_path(source_path: str) -> tuple[str, str] | ErrorCode:
    """
    Find where a file on a mergerfs mount is actually stored.

    Equivalent to `getfattr -n user.mergerfs.fullpath <source_path>`.

    :param source_path: Absolute path of a file inside a mergerfs mount
    :return: (actual_path, relative_path), e.g.
             ("/run/media/wisky/test2/UofT_document/a.md", "UofT_document/a.md"),
             or ErrorCode.NOT_ON_MERGERFS if the path is not on a mergerfs mount
             or mergerfs xattrs are disabled
    """
    error = validate_tracking_path(source_path)
    if error is not None:
        return error

    try:
        actual_path = os.fsdecode(os.getxattr(source_path, MERGERFS_FULLPATH_XATTR))
        relative_path = os.fsdecode(os.getxattr(source_path, MERGERFS_RELPATH_XATTR))
    except OSError:
        return ErrorCode.NOT_ON_MERGERFS

    return actual_path, relative_path.lstrip("/")


class MoveHandle:
    """
    A file move running in the background, returned by start_mergerfs_move().

    None of the methods block except wait() and cancel(). The handle does not
    use a background thread: progress is measured when progress() is called.

    Attributes:
        source_path: Path of the file inside the mergerfs mount.
        actual_path: Path on the partition the file is being moved from.
        destination_path: Path on the partition the file is being moved to.
        total_bytes: Size of the file when the move started.
    """

    def __init__(self, source_path: str, actual_path: str, destination_path: str,
                 total_bytes: int, process: subprocess.Popen):
        self.source_path = source_path
        self.actual_path = actual_path
        self.destination_path = destination_path
        self.total_bytes = total_bytes

        self._process = process
        self._result: str | ErrorCode | None = None
        self._last_progress = 0.0
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        """
        :return: True while mv is still running
        """
        with self._lock:
            self._update_locked()
            return self._result is None

    def progress(self) -> float:
        """
        Percentage of the file copied so far, from 0.0 to 100.0.

        Measured as the destination file's size against the source size.
        Stays at 99.9 at most until mv has finished, and is 100.0 only after
        a successful move. After a failed or cancelled move, the last value
        measured is returned.

        :return: Percentage moved
        """
        with self._lock:
            self._update_locked()
            if self._result == self.destination_path:
                return 100.0
            if self._result is not None:
                return self._last_progress
            if self.total_bytes > 0:
                try:
                    copied = os.path.getsize(self.destination_path)
                except OSError:
                    copied = 0
                self._last_progress = min(copied / self.total_bytes, 0.9999)
            return self._last_progress

    def result(self) -> str | ErrorCode | None:
        """
        :return: None while still running; then the destination path on
                 success, or ErrorCode.MOVE_FAILED / ErrorCode.MOVE_CANCELLED
        """
        with self._lock:
            self._update_locked()
            return self._result

    def wait(self, timeout: float | None = None) -> str | ErrorCode | None:
        """
        Block until the move finishes, or until timeout seconds have passed.

        :param timeout: Seconds to wait, or None to wait until finished
        :return: Same as result(); None if the timeout passed first
        """
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        return self.result()

    def cancel(self) -> bool:
        """
        Stop the move.

        If the original file is still on the source partition, the partial
        copy on the destination is deleted and the result becomes
        ErrorCode.MOVE_CANCELLED. If mv had already finished moving the file,
        the move counts as successful and nothing is deleted.

        :return: True if the move was cancelled, False if it had already
                 finished (successfully or not)
        """
        with self._lock:
            self._update_locked()
            if self._result is not None:
                return False

            self._process.terminate()
            try:
                self._process.wait(timeout=CANCEL_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

            if os.path.lexists(self.actual_path):
                try:
                    os.remove(self.destination_path)
                except OSError:
                    pass
                self._result = ErrorCode.MOVE_CANCELLED
                return True

            self._result = self.destination_path
            return False

    def _update_locked(self) -> None:
        if self._result is not None:
            return
        returncode = self._process.poll()
        if returncode is None:
            return

        moved = not os.path.lexists(self.actual_path) and os.path.lexists(self.destination_path)
        if returncode == 0 or moved:
            self._result = self.destination_path
        else:
            self._result = ErrorCode.MOVE_FAILED


def start_mergerfs_move(source_path: str, destination_mount: str) -> MoveHandle | ErrorCode:
    """
    Start moving a file in a mergerfs pool from the partition that holds it
    to another partition, keeping the same relative path. Returns immediately.

    Calls `mv` on the underlying partition paths, not on the mergerfs path.
    The destination directory must already exist. The destination path must be unused.

    :param source_path: Absolute path of the file inside the mergerfs mount
    :param destination_mount: Absolute mount point of the destination partition
    :return: MoveHandle for the running move, or an ErrorCode if it could not
             start: INVALID_PATH, PATH_NOT_ABSOLUTE, FILE_NOT_FOUND, NOT_A_DIRECTORY,
             NOT_ON_MERGERFS, ALREADY_ON_DESTINATION, FILE_ALREADY_EXISTS or
             MOVE_FAILED (mv could not be run)
    """
    for path in (source_path, destination_mount):
        error = validate_tracking_path(path)
        if error is not None:
            return error
    if not os.path.isfile(source_path):
        return ErrorCode.FILE_NOT_FOUND
    if not os.path.isdir(destination_mount):
        return ErrorCode.NOT_A_DIRECTORY

    resolved = resolve_mergerfs_path(source_path)
    if isinstance(resolved, ErrorCode):
        return resolved
    actual_path, relative_path = resolved
    destination_path = os.path.join(destination_mount, relative_path)

    if os.path.realpath(actual_path) == os.path.realpath(destination_path):
        return ErrorCode.ALREADY_ON_DESTINATION
    if os.path.lexists(destination_path):
        return ErrorCode.FILE_ALREADY_EXISTS

    try:
        total_bytes = os.path.getsize(actual_path)
    except OSError:
        return ErrorCode.FILE_NOT_FOUND

    try:
        process = subprocess.Popen(
            ["mv", "--", actual_path, destination_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return ErrorCode.MOVE_FAILED

    return MoveHandle(source_path, actual_path, destination_path, total_bytes, process)


def move_mergerfs_file(
    source_path: str,
    destination_mount: str,
    on_progress: Callable[[float], None] | None = None,
    progress_interval: float = DEFAULT_PROGRESS_INTERVAL,
) -> str | ErrorCode:
    """
    Blocking version of start_mergerfs_move(): waits until the move finishes.

    :param source_path: Absolute path of the file inside the mergerfs mount
    :param destination_mount: Absolute mount point of the destination partition
    :param on_progress: Called with the percentage moved (0.0 to 100.0), only
                        when the value changes
    :param progress_interval: Seconds between progress checks
    :return: New actual path of the file on the destination partition, or an
             ErrorCode (see start_mergerfs_move; also MOVE_FAILED if mv fails)
    """
    handle = start_mergerfs_move(source_path, destination_mount)
    if isinstance(handle, ErrorCode):
        return handle

    last_reported = None
    while True:
        result = handle.wait(timeout=progress_interval)
        percent = handle.progress()
        if on_progress is not None and percent != last_reported:
            last_reported = percent
            on_progress(percent)
        if result is not None:
            return result