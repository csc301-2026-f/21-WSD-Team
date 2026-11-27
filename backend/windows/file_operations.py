# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import os
import threading
import shutil

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable,Any

from .device_provider import DeviceProvider


class MoveErrorCode(str, Enum):
    INVALID_SOURCE = "invalid_source"
    INVALID_DESTINATION = "invalid_destination"
    SOURCE_NOT_ON_MANAGED_DEVICE = "source_not_on_managed_device"
    DESTINATION_NOT_ON_MANAGED_DEVICE = "destination_not_on_managed_device"
    AMBIGUOUS_DEVICE = "ambiguous_device"
    SAME_FILE = "same_file"
    DESTINATION_EXISTS = "destination_exists"
    DESTINATION_PARENT_MISSING = "destination_parent_missing"
    MOVE_FAILED = "move_failed"
    MOVE_CANCELLED = "move_cancelled"
    COPPIED_BUT_ERRORED = "coppied_but_errored"


class MoveStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COPPIED = "coppied"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class MoveError(Exception):
    def __init__(self, code: MoveErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)#field may be none if move_error is not none
class MoveResult:
    move_error: MoveError | None = None
    source_path: str | None = None
    destination_path: str | None = None
    bytes_moved: int | None = None
    total_bytes: int | None = None


@dataclass(frozen=True)
class _ResolvedPath:
    path: Path
    device_id: int
    mount_point: str
    relative_path: Path


class WindowsFileMover:
    """Move files between physical devices known to DeviceProvider.
    The destination directory hierarchy must already exist. The source's
    path relative to its volume root is preserved on the destination volume"""
    def __init__(
        self,
        device_provider: DeviceProvider,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        self._device_provider = device_provider
        self._chunk_size = chunk_size

    def start_move(
        self,
        source_path: str | os.PathLike[str],
        destination_mount: str,
        destination_rel_path: Path | None = None
    ) -> tuple[MoveHandle|None , MoveError|None]:
        """Validate a move and start it on a background thread"""
        src, mve = self._resolve_source(source_path)
        if mve is not None: return (None,mve)
        else: source, source_stat = src
        dst, mve = self._resolve_destination_mount(destination_mount)
        if mve is not None: return (None,mve)
        destination_root, destination_device_id = dst
        if destination_rel_path is not None:
            destination = destination_root / destination_rel_path
        else:
            destination = destination_root / source.relative_path 
        mve = self._check_destination(destination,destination_root,source) #error checks
        if mve is not None: return (None,mve)
        return (MoveHandle(
            source_path=source.path,
            destination_path=destination,
            total_bytes=source_stat.st_size,
            chunk_size=self._chunk_size,
        ),None)

    def move_file(
        self,
        source_path: str | os.PathLike[str],
        destination_mount: str,
        destination_rel_path: Path | None = None,
        progress_callback: Callable[[float], None] | None = None,
        cancel_call: Callable[[None],bool] | None = None
    ) -> MoveResult:
        """Blocking convenience wrapper around start_move(), 
            pass in a progress callback function to receive 
            completion percentages and a cancel callable that you
            set to true when cancelling, it is checked once every 0.1 seconds.
            pass in a relative destination path to move it to dst_mnt//dst_path instead of
            dst_mnt//src_path"""
        handle, mve = self.start_move(source_path, destination_mount, destination_rel_path)
        if mve is not None: return MoveResult(move_error=mve)
        while not handle.wait(timeout=0.1):
            if progress_callback is not None: progress_callback(handle.progress)
            if cancel_call is not None and cancel_call(): handle.cancel(0.1)
        if progress_callback is not None: progress_callback(handle.progress)
        if handle.status == MoveStatus.COPPIED:
            try:
                handle.switch()
            except Exception:
                return MoveResult(move_error=MoveError(
                    MoveErrorCode.COPPIED_BUT_ERRORED,
                    "Could not swap file ownership."
                ))
        if handle.error is not None: 
            if handle.status != MoveStatus.COPPIED:
                return MoveResult(move_error=
                    MoveError(MoveErrorCode.MOVE_FAILED, handle.error.code))
            else:
                return MoveResult(move_error=
                    MoveError(MoveErrorCode.COPPIED_BUT_ERRORED, handle.error.code))
        if handle.status == MoveStatus.CANCELLED:
            return MoveResult(
            move_error=MoveError(
                MoveErrorCode.MOVE_CANCELLED,
                "Move cancelled."),
            source_path=str(handle.source_path),
            destination_path=str(handle.destination_path),
            bytes_moved=handle.bytes_moved,
            total_bytes=handle.total_bytes,
            )
        result = handle.result
        if result is None:
            return MoveResult(move_error=MoveError(
                MoveErrorCode.MOVE_FAILED,
                "Move ended without producing a result.",
            ))
        return result

    def _resolve_source(
        self,
        source_path: str | os.PathLike[str],
    ) -> tuple[tuple[_ResolvedPath,Any]|None,MoveError|None]:
        raw_path = Path(source_path)

        if not raw_path.is_absolute():
            return (None,MoveError(
                MoveErrorCode.INVALID_SOURCE,
                "Source path must be absolute.",
            ))
        if raw_path.is_symlink():
            return (None,MoveError(
                MoveErrorCode.INVALID_SOURCE,
                "Unsupported symlink source.",
            ))
        try: resolved_path = raw_path.resolve(strict=True)
        except OSError:
            return (None,MoveError(
                MoveErrorCode.INVALID_SOURCE,
                f"Source file does not exist: {raw_path}",
            ))
        matches: list[_ResolvedPath] = []
        for device in self._device_provider.list_devices():
            for mount_point in device.mount_points:
                root = self._normalise_mount_point(mount_point)
                try: relative_path = resolved_path.relative_to(root)
                except ValueError:
                    continue
                matches.append(
                    _ResolvedPath(
                        path=resolved_path,
                        device_id=device.device_id,
                        mount_point=mount_point,
                        relative_path=relative_path,
                    )
                )
        if not matches:
            return (None,MoveError(
                MoveErrorCode.SOURCE_NOT_ON_MANAGED_DEVICE,
                f"Source is not on a managed device: {resolved_path}",
            ))
        device_ids = {match.device_id for match in matches}
        if len(device_ids) != 1:
            return (None,MoveError(
                MoveErrorCode.AMBIGUOUS_DEVICE,
                f"Source maps to multiple physical devices: {resolved_path}",
            ))
        # Prefer the longest match, assumed most specific
        source = max(matches,key=lambda match: len(str(match.mount_point)))
        try: source_stat = source.path.stat()
        except OSError:
            return (None,MoveError(
                MoveErrorCode.INVALID_SOURCE,
                f"Unable to inspect source file: {source.path}",
            ))
        if not source.path.is_file():
            return (None,MoveError(
                MoveErrorCode.INVALID_SOURCE,
                "Source path must be a regular file.",
            ))
        return ((source,source_stat),None)

    def _resolve_destination_mount(
        self,
        destination_mount: str,
    ) -> tuple[tuple[Path, int]|None,MoveError|None]:
        if not isinstance(destination_mount, str) or not destination_mount:
            return (None,MoveError(
                MoveErrorCode.INVALID_DESTINATION,
                "A destination drive letter is required.",
            ))
        matches: list[tuple[Path, int]] = []
        for device in self._device_provider.list_devices():
            for mount_point in device.mount_points:
                if mount_point.casefold() == destination_mount.casefold():
                    matches.append((self._normalise_mount_point(mount_point),
                                    device.device_id,))
        if not matches:
            return (None,MoveError(
                MoveErrorCode.DESTINATION_NOT_ON_MANAGED_DEVICE,
                f"Destination is not a managed mount point: {destination_mount}",
            ))
        device_ids = {device_id for _, device_id in matches}
        if len(device_ids) != 1:
            return (None,MoveError(
                MoveErrorCode.AMBIGUOUS_DEVICE,
                f"Destination maps to multiple physical devices: {destination_mount}",
            ))

        return (matches[0],None)

    @staticmethod
    def _normalise_mount_point(mount_point: str) -> Path:
        # convert D: and D:\\ to only D:\\
        root_text = mount_point.rstrip("\\/")
        if len(root_text) == 2 and root_text[1] == ":":
            root_text += os.sep
        return Path(root_text).resolve()

    @staticmethod
    def _check_destination(destination:Path, destination_root:Path, 
                           source:_ResolvedPath)-> MoveError | None:
        """destination error checks, returns nothing"""
        try: destination_parent = destination.parent.resolve(strict=True)
        except OSError:
            return MoveError(
                MoveErrorCode.DESTINATION_PARENT_MISSING,
                f"Destination directory does not exist: {destination.parent}",
            )
        if not destination_parent.is_relative_to(destination_root):
            return MoveError(
                MoveErrorCode.INVALID_DESTINATION,
                "Destination resolves outside the selected volume.",
            )
        if os.path.normcase(str(source.path)) == os.path.normcase(str(destination)):
            return MoveError(
                MoveErrorCode.SAME_FILE,
                "Source and destination are the same path.",
            )
        if os.path.lexists(destination):
            return MoveError(
                MoveErrorCode.DESTINATION_EXISTS,
                f"Destination already exists: {destination}",
            )

class MoveHandle:
    def __init__(
        self,
        *,
        source_path: Path,
        destination_path: Path,
        total_bytes: int,
        chunk_size: int = 1024 * 1024,
    ):
        self.source_path = source_path
        self.destination_path = destination_path
        self.total_bytes = total_bytes
        self.chunk_size = chunk_size

        self.temp_path = destination_path.with_name(self.destination_path.name + ".moving")
        self.bytes_moved = 0
        self.status = MoveStatus.PENDING
        self.result: MoveResult | None = None
        self.error: MoveError | None = None

        self._cancel_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def progress(self) -> float:
        if self.total_bytes == 0:
            return 100.0 if self.status in {MoveStatus.COMPLETED,MoveStatus.COPPIED} else 0.0
        return min(100.0, self.bytes_moved / self.total_bytes * 100)

    def cancel(self, timeout_sec=None):
        self._cancel_event.set()
        self._thread.join(timeout_sec)
        self._cleanup()
        return not self._thread.is_alive()

    def wait(self, timeout_sec=None) -> bool:
        self._thread.join(timeout_sec)
        done = not self._thread.is_alive()
        #thread ended but all data is on disk, keep and try to recover later
        if (done and not self.status == MoveStatus.COPPIED): self._cleanup()
        return done

    def _run(self):
        temp_path = self.temp_path
        try:
            self.status = MoveStatus.RUNNING
            with self.source_path.open("rb") as src, temp_path.open("xb") as dst:
                while chunk := src.read(self.chunk_size):
                    if self._cancel_event.is_set():
                        self.status = MoveStatus.CANCELLED
                        return
                    dst.write(chunk)
                    self.bytes_moved += len(chunk)
            shutil.copystat(self.source_path, temp_path)
            if self._cancel_event.is_set():
                self.status = MoveStatus.CANCELLED
                return
            self.status = MoveStatus.COPPIED
        except Exception as exc:
            self.error = exc
            self.status = MoveStatus.FAILED
            return
        #only reaches this when file is on both disks, failing now is recoverable
        if self.status != MoveStatus.COPPIED: return
        try: self.switch()
        except Exception as exc:
            self.error = exc
            return

    
    def switch(self):
        """switches the ownership of the file in storage.
           if need to call this outside this class, wrap in try block"""
        self.temp_path.rename(self.destination_path)
        self.source_path.unlink()
        self.result = MoveResult(
            source_path=str(self.source_path),
            destination_path=str(self.destination_path),
            bytes_moved=self.bytes_moved,
            total_bytes=self.total_bytes,
        )
        self.status = MoveStatus.COMPLETED
    
    def _cleanup(self):
        temp_path = self.temp_path
        if temp_path.exists(): temp_path.unlink()
        return
