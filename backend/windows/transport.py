from collections.abc import Callable
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import etw

from .contracts import CollectionHealth

#magic number found on microsoft documentation for our kind of event tracing
KERNEL_TRACE_GUID = "{9E814AAD-3204-11D2-9A82-006008A86939}"


class EtwTransport:
    """Real-time Windows kernel disk-I/O ETW transport.

    Requires pywintrace and a Windows environment with permission
    to start the NT Kernel Logger session.

    It works by putting a piece of code in the ETW framework that gets given events.
    It filters the IO ones and applies a callback to each, getting us the event info.
    """

    def __init__(self) -> None:
        self._session: Any | None = None
        self._on_record: Callable[[dict[str, Any]], None] | None = None
        #the function to process the IO operations received. type RawIoEvent->None
        self._lock = Lock()
        self._running = False
        self._events_received = 0
        self._last_event_utc: str | None = None
        self._last_error: str | None = None

    def start(
        self,
        on_record: Callable[[dict[str, Any]], None],
    ) -> None:
        with self._lock:
            if self._running:
                return

            self._on_record = on_record
            self._last_error = None

        try:
            # Create fresh provider objects for each session.
            provider = etw.ProviderInfo(
                "Windows Kernel Trace",
                etw.GUID(KERNEL_TRACE_GUID),
                any_keywords=0x00000100  # DISK_IO
                            | 0x00000200  # DISK_FILE_IO
                            | 0x00000400  # DISK_IO_INIT
                            | 0x02000000  # FILE_IO
                            | 0x04000000  # FILE_IO_INIT, #documented on microsoft docs as disk_io and disk_io_init
            )

            session = etw.ETW(
                session_name="NT Kernel Logger",
                providers=[provider],
                event_callback=self._handle_event,
            )

            session.start()

            with self._lock:
                self._session = session
                self._running = True

        except Exception as exc:
            with self._lock:
                self._last_error = f"{type(exc).__name__}: {exc}"
            raise

    def _handle_event(self, item: Any) -> None:
        #Adapt pywintrace's (event_id, event_data) callback.
        #print(f"transport got called for event {item[1]}")
        try:
            if (
                isinstance(item, tuple)
                and len(item) == 2
                and isinstance(item[1], dict)
            ):
                event_id, payload = item
                record = dict(payload)
                record["_etw_event_id"] = event_id
            elif isinstance(item, dict):
                record = dict(item)
            else:
                return

            with self._lock:
                callback = self._on_record
                self._events_received += 1
                self._last_event_utc = (
                    datetime.now(timezone.utc)
                    .isoformat(timespec="microseconds")
                    .replace("+00:00", "Z")
                )

            if callback is not None:
                callback(record)

        except Exception as exc:
            with self._lock:
                self._last_error = f"{type(exc).__name__}: {exc}"

    def stop(self) -> None:
        with self._lock:
            session = self._session
            self._session = None
            self._running = False

        if session is not None:
            try:
                session.stop()
            except Exception as exc:
                with self._lock:
                    self._last_error = f"{type(exc).__name__}: {exc}"
                raise

    def get_health(self) -> CollectionHealth:
        with self._lock:
            return CollectionHealth(
                running=self._running,
                events_received=self._events_received,
                events_lost=0,  # Loss tracking is deferred for this version.
                last_event_utc=self._last_event_utc,
                last_error=self._last_error,
            )
