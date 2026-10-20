#pass etw events through a decoder and hand them off
from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID
from time import time_ns


from .contracts import CollectionHealth, RawIoEvent
from .transport import EtwTransport

DISK_IO_PROVIDER_GUID = "3d6fa8d4-fe05-11d0-9dda-00c04fd7ba7c"
#according to etw api, if an event doesnt have this guid, it is not from the IO read/write provider

# Windows kernel DiskIo completion event opcodes.
OPCODE_READ = 10
OPCODE_WRITE = 11

class EtwDecoder:
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
            if normalized_guid.lower() != DISK_IO_PROVIDER_GUID:
                return None    
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
            # Process name is not guaranteed to be present in DiskIo records.
            process_name = record.get("ProcessName")
            if not isinstance(process_name, str) or not process_name.strip():
                process_name = record.get("ImageFileName")
            if not isinstance(process_name, str) or not process_name.strip():
                process_name = None
            # This is collection time, not the original event time.
            observed_timestamp_ns = time_ns()
            return RawIoEvent(
                timestamp_ns=observed_timestamp_ns,
                operation=operation,
                pid=pid,
                process_start_time_utc=None,
                process_name=process_name,
                device_id=f"disk:{disk_number}",
                transferred_bytes=transferred_bytes,
                duration_ns=None,
                file_id=None,
                path=None,
                file_size_bytes=None,
                file_attribution_verified=False,
                source="windows_etw",
            )
        except (TypeError, ValueError, OverflowError):
        # Malformed or incomplete records are discarded.
            return None

    @staticmethod
    def _integer(value: Any) -> int | None:
        """Accept integer values, but reject booleans and numeric strings."""
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value


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
