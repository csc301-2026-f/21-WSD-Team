# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
#pass etw events through a decoder and hand them off
from collections.abc import Callable
from typing import Any
from uuid import UUID
from time import time_ns


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

class EtwDecoder:
    def __init__(self, device_provider:DeviceProvider):
        self._file_name_map: dict[int,str] = dict()
        self._file_location_map: dict[int,(int,int)] = dict()
        self._device_provider: DeviceProvider = device_provider

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
            process_name = None
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
        if opcode == OPCODE_FILE_READ:
            operation = "read"
        elif opcode == OPCODE_FILE_WRITE:
            operation = "write"
        elif opcode in {OPCODE_FILE_RUNDOWN, 
                        OPCODE_FILE_NAME, 
                        OPCODE_FILE_CREATE}:
            self._add_mapping(record)
            return None
        else:  # Ignore initiation and other event types.
            return None
        pid = self._integer(header.get("ProcessId"))
        transferred_bytes = self._integer(record.get("IoSize"))        
        if pid is None or transferred_bytes is None:
            return None    
        if pid < 0 or transferred_bytes < 0:
            return None    
        # Process name may not be in FileIO
        process_name = record.get("ProcessName")
        if not isinstance(process_name, str) or not process_name.strip():
            process_name = record.get("ImageFileName")
        if not isinstance(process_name, str) or not process_name.strip():
            process_name = None
        file_id = self._parse_pointer(record.get("FileKey")) #FileObject is a field but has a different purpose
        if file_id is None:
            return None
        path = self._file_name_map.get(file_id)
        disk_number,offset = self._file_location_map.get(file_id)
        #a fileIO is only useful if at least the path is known
        if path is None: 
            return None
        path_letter = self._get_letter(disk_number,offset)
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
                    file_attribution_verified=True,
                    source="fileIO",
                )
    
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


    

    """def _get_process_name(self,pid) #not for D2
        try:
            return psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None"""
    

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
    ) -> None:
        def on_record(record: dict[str, Any]) -> None:
            event = self._decoder.decode(record)
            if event is not None:
                on_event(event)

        self._transport.start(on_record)

    def stop(self) -> None:
        self._transport.stop()

    def get_health(self) -> CollectionHealth:
        return self._transport.get_health()
