# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
#pass etw events through a decoder and hand them off
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from time import time_ns

import psutil


from .contracts import CollectionHealth, RawIoEvent
from .transport import EtwTransport
from .device_provider import DeviceProvider

DISK_IO_PROVIDER_GUID = "3d6fa8d4-fe05-11d0-9dda-00c04fd7ba7c"
FILE_IO_PROVIDER_GUID = "90cbdc39-4a3e-11d1-84f4-0000f80464e3"
#according to etw api, if an event doesnt have this guid, 
#it is not from the IO read/write providers and can be dropped

# Windows kernel event opcodes.
OPCODE_READ = 10
OPCODE_WRITE = 11

OPCODE_FILE_READ = 67
OPCODE_FILE_WRITE = 68

OPCODE_FILE_NAME = 0
OPCODE_FILE_CREATE = 32
OPCODE_FILE_RUNDOWN = 36
OPCODE_FILE_OPEN = 64
OPCODE_FILE_CLOSE = 66
OPCODE_FILE_DELETE = 35

class EtwDecoder:
    def __init__(self, device_provider:DeviceProvider, *, resolve_open_paths=True, recover_late_names=True):
        self._file_name_map: dict[int,str] = dict()
        self._file_location_map: dict[int,(int,int)] = dict()
        self._device_provider: DeviceProvider = device_provider
        self._open_file_name_map = dict()
        self._pending = dict()
        self._pending_by_key = dict()
        self._file_generations = dict()
        self._open_sequence = 0
        self._resolved = []
        self._resolve_open_paths = resolve_open_paths
        self._recover_late_names = recover_late_names
        self._path_diagnostics = dict(open_events=0, name_events=0,
                                     resolved_on_read_write=0, resolved_from_openpath=0, recovered_after_mapping=0,
                                     pending_expired_or_reused=0)

    def decode(
        self, record: dict[str, Any]
    ) -> RawIoEvent | None:
        """Return a normalized completed I/O event, if applicable."""
        try:
            header = record.get("EventHeader")
            if not isinstance(header, dict):
                return None
            provider_id = header.get("ProviderId")
            if not isinstance(provider_id, str):
                return None        
            try:
                normalized_guid = str(UUID(provider_id.strip("{}")))
            except (ValueError, AttributeError):
                return None
            if normalized_guid.lower() == DISK_IO_PROVIDER_GUID:
                return self._diskIO_event_decoder(record,header) 
            if normalized_guid.lower() == FILE_IO_PROVIDER_GUID:
                return self._fileIO_event_decoder(record,header)   
        except (TypeError, ValueError, OverflowError):
        # Malformed or incomplete records are discarded.
            return None
        
    @staticmethod
    def _parse_pointer(value: Any) -> int | None:
        """Normalize an ETW pointer represented as an int or hex string."""
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, str):
            value = value.strip()
            try:
                if value.lower().startswith("0x"):
                    result = int(value, 16)
                else:
                    return None
                return result if result >= 0 else None
            except ValueError:
                return None
        return None
        
    @staticmethod
    def _integer(value: Any) -> int | None:
        """Accept integer values, but reject booleans and numeric strings."""
        if isinstance(value, str):
            return int(value)
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value

    def _diskIO_event_decoder(self, record, header):
        descriptor = header.get("EventDescriptor")
        if not isinstance(descriptor, dict):
            return None
        opcode = self._integer(descriptor.get("Opcode"))
        if opcode == OPCODE_READ:
            operation = "read"
        elif opcode == OPCODE_WRITE:
            operation = "write"
        else:  # Ignore initiation and other event types.
            return None
        pid = self._integer(header.get("ProcessId"))
        disk_number = self._integer(record.get("DiskNumber"))
        transferred_bytes = self._integer(record.get("TransferSize"))
        if pid is None or disk_number is None or transferred_bytes is None:
            return None    
        if pid < 0 or disk_number < 0 or transferred_bytes < 0:
            return None    
        # Process name may not be in DiskIO
        process_name = record.get("ProcessName")
        if not isinstance(process_name, str) or not process_name.strip():
            process_name = record.get("ImageFileName")
        if not isinstance(process_name, str) or not process_name.strip():
            process_name = self._get_process_name(pid)
        # This is collection time, not the original event time.
        observed_timestamp_ns = time_ns()
        # get file path from the current mapping
        file_id = self._parse_pointer(record.get("FileObject"))
        path = None
        path_letter = None
        if file_id is not None:
            offset = self._integer(record.get("ByteOffset"))
            if offset is not None and offset > 0: #record location for fileIO
                self._file_location_map[file_id] = (disk_number,offset) 
                path_letter = self._get_letter(disk_number,offset)
            path = self._file_name_map.get(file_id)
        file_attribution_verified = (path is not None)
        return RawIoEvent(
            timestamp_ns=observed_timestamp_ns,
            operation=operation,
            pid=pid,
            process_start_time_utc=None,
            process_name=process_name,
            device_id=disk_number,
            transferred_bytes=transferred_bytes,
            duration_ns=None,
            file_id=file_id,
            path=path,
            decoded_drive_letter=path_letter,
            file_size_bytes=None,
            file_attribution_verified=file_attribution_verified,
            source="diskIO",
        )

    def _fileIO_event_decoder(self, record, header):
        observed_timestamp_ns = time_ns()
        descriptor = header.get("EventDescriptor")
        if not isinstance(descriptor, dict):
            return None
        opcode = self._integer(descriptor.get("Opcode"))
        if opcode == OPCODE_FILE_OPEN:
            self._path_diagnostics["open_events"] += 1
            file_object = self._parse_pointer(record.get("FileObject"))
            if file_object is not None:
                # FileObject may be reused for a later open. Never attach its
                # old pending requests to the new file's OpenPath.
                self._open_file_name_map.pop(file_object, None)
                self._open_sequence += 1
                if len(self._file_generations) >= 65536:
                    self._file_generations.clear()
                    self._open_file_name_map.clear()
                self._file_generations[file_object] = self._open_sequence
                path = record.get("OpenPath")
                if self._resolve_open_paths and isinstance(path, str) and path.strip():
                    self._open_file_name_map[file_object] = path
            return None
        elif opcode == OPCODE_FILE_CLOSE:
            self._open_file_name_map.pop(self._parse_pointer(record.get("FileObject")), None)
            return None
        elif opcode == OPCODE_FILE_DELETE:
            self._file_name_map.pop(self._parse_pointer(record.get("FileObject")), None)
            return None
        elif opcode == OPCODE_FILE_READ:
            operation = "read"
        elif opcode == OPCODE_FILE_WRITE:
            operation = "write"
        elif opcode in {OPCODE_FILE_RUNDOWN, 
                        OPCODE_FILE_NAME, 
                        OPCODE_FILE_CREATE}:
            self._add_mapping(record)
            self._path_diagnostics["name_events"] += 1
            self._resolve_pending(self._parse_pointer(record.get("FileObject")))
            return None
        else:  # Ignore initiation and other event types.
            return None
        #print(f"{operation} , FileKey: {record.get("FileKey")}, FileObject: {record.get("FileObject")}, maps:{len(self._file_name_map)}, time:{observed_timestamp_ns}")
        pid = self._integer(header.get("ProcessId"))
        transferred_bytes = self._integer(record.get("IoSize"))        
        if pid is None or transferred_bytes is None:
            return None    
        if pid < 0 or transferred_bytes < 0:
            return None    
        process_start, observed_name = self._get_process_identity(pid, header)
        # Process name may not be in FileIO
        process_name = record.get("ProcessName")
        if not isinstance(process_name, str) or not process_name.strip():
            process_name = record.get("ImageFileName")
        if not isinstance(process_name, str) or not process_name.strip():
            process_name = observed_name
        file_key = self._parse_pointer(record.get("FileKey")) #determines path
        file_object = self._parse_pointer(record.get("FileObject")) # stable ID on fileIO layer
        if file_key is None or file_object is None:
            return None
        # path = self._file_name_map.get(file_key)
        # location = self._file_location_map.get(file_key)
        # if location: disk_number,offset = location
        # else: 
        #     disk_number=None
        #     offset=None
        # #since the fileObject field is stable between create and close calls, path may be correlated later
        # path_letter = self._get_letter(disk_number,offset)
        
        # Resolve the file directly from its NT volume path.
        # DiskIO offsets may point to a different partition on the same disk.
        nt_path = self._open_file_name_map.get(file_object)
        resolved = self._device_provider.resolve_nt_file_path(nt_path)
        if resolved is not None:
            self._path_diagnostics["resolved_from_openpath"] += 1
        if resolved is None:
            resolved = self._device_provider.resolve_nt_file_path(self._file_name_map.get(file_key))

        if resolved is not None:
            path, disk_number = resolved
            path_letter = path[:2]
        else:
            # Keep unknown attribution unresolved rather than reporting
            # an incorrect drive letter.
            path = None
            disk_number = None
            path_letter = None
        event = RawIoEvent(
                    timestamp_ns=observed_timestamp_ns,
                    operation=operation,
                    pid=pid,
                    process_start_time_utc=process_start,
                    process_name=process_name,
                    device_id=disk_number,
                    transferred_bytes=transferred_bytes,
                    duration_ns=None,
                    file_id=file_object,
                    path=path,
                    decoded_drive_letter=path_letter,
                    file_size_bytes=None,
                    file_attribution_verified=(path is not None),
                    source="fileIO",
                )
        if path is not None:
            self._path_diagnostics["resolved_on_read_write"] += 1
        elif self._recover_late_names:
            identity = id(event)
            self._pending[identity] = (file_key, file_object, event, self._file_generations.get(file_object))
            self._pending_by_key.setdefault(file_key, set()).add(identity)
            # Bound unresolved metadata independently of the I/O history.
            cutoff = observed_timestamp_ns - 60_000_000_000
            while self._pending:
                oldest = next(iter(self._pending))
                if len(self._pending) <= 50000 and self._pending[oldest][2].timestamp_ns >= cutoff:
                    break
                self._remove_pending(oldest)
                self._path_diagnostics["pending_expired_or_reused"] += 1
        return event

    def _remove_pending(self, identity):
        item = self._pending.pop(identity)
        identities = self._pending_by_key[item[0]]
        identities.discard(identity)
        if not identities:
            self._pending_by_key.pop(item[0])
        return item

    def _resolve_pending(self, file_key):
        cutoff = time_ns() - 60_000_000_000
        # Only revisit requests affected by this name event, not every pending
        # file on every callback. Keep the tracing thread's work bounded.
        for identity in list(self._pending_by_key.get(file_key, ())):
            _, file_object, event, generation = self._pending[identity]
            if event.timestamp_ns < cutoff or generation != self._file_generations.get(file_object):
                self._remove_pending(identity)
                self._path_diagnostics["pending_expired_or_reused"] += 1
                continue
            nt_path = self._file_name_map.get(file_key)
            resolved = self._device_provider.resolve_nt_file_path(nt_path)
            if resolved is None:
                continue
            self._remove_pending(identity)
            path, disk_number = resolved
            self._resolved.append((event, replace(event, path=path, device_id=disk_number,
                decoded_drive_letter=path[:2], file_attribution_verified=True)))
            self._path_diagnostics["recovered_after_mapping"] += 1

    def take_resolved_events(self):
        resolved = self._resolved
        self._resolved = []
        return resolved

    def get_path_diagnostics(self):
        return {**self._path_diagnostics, "pending_paths": len(self._pending)}
    
    def _add_mapping(self,record):
        fileObject = self._parse_pointer(record.get("FileObject"))
        if fileObject is None: 
            return
        filePath = record.get("FileName")
        if not isinstance(filePath, str) or not filePath.strip():
            return
        self._file_name_map[fileObject] = filePath
        return

    def _get_letter(self,disk_number,offset):
        return self._device_provider.resolve_drive_letter(disk_number,offset)


    def _get_process_name(self,pid):
        try:
            return psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def _get_process_identity(self, pid, header):
        """Do not assign a buffered event to a newer process reusing its PID."""
        try:
            ticks = self._integer(header.get("TimeStamp"))
        except (TypeError, ValueError, OverflowError):
            return None, None
        if ticks is None or ticks < 116444736000000000:
            return None, None
        event_time_ns = (ticks - 116444736000000000) * 100
        try:
            process = psutil.Process(pid)
            started = process.create_time()
            # Some protected/system processes report zero, not a real start time.
            if started <= 0 or int(started * 1_000_000_000) > event_time_ns + 1000:
                return None, None
            name = process.name()
            if not process.is_running():
                return None, None
            timestamp = datetime.fromtimestamp(started, timezone.utc).isoformat().replace("+00:00", "Z")
            return timestamp, name
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, ValueError, OverflowError):
            return None, None
    

class EtwSource:
    def __init__(
        self,
        transport: EtwTransport,
        decoder: EtwDecoder,
    ):
        self._transport = transport
        self._decoder = decoder

    def start(
        self,
        on_event: Callable[[RawIoEvent], None],
        on_resolved=None,
    ) -> None:
        def on_record(record: dict[str, Any]) -> None:
            event = self._decoder.decode(record)
            if event is not None:
                on_event(event)
            resolved = self._decoder.take_resolved_events()
            if resolved and on_resolved is not None:
                # Update attribution, not the I/O count or original timestamp.
                on_resolved(resolved)

        self._transport.start(on_record)

    def stop(self) -> None:
        self._transport.stop()

    def get_health(self) -> CollectionHealth:
        return self._transport.get_health()

""" 
pointer baton pass summary:
    FileIO.r/w->FileKey ~ FileIO.name->FileObject ~ DiskIO.r/w->FileObject
    FileIO.r/w->FileObject ~ stable FileID across FileIO
"""
