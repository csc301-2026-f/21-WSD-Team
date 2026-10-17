#pass etw events through a decoder and hand them off
from collections.abc import Callable
from typing import Any, Protocol

from .contracts import CollectionHealth, RawIoEvent
from .transport import EtwTransport


class EtwDecoder(Protocol):
    def decode(
        self, record: dict[str, Any]
    ) -> RawIoEvent | None:
        """Return a normalized completed I/O event, if applicable."""
        ...


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
