#abstract for now, can't be wrong yet
from collections.abc import Callable
from typing import Any, Protocol

from .contracts import CollectionHealth


class EtwTransport(Protocol):
    def start(
        self,
        on_record: Callable[[dict[str, Any]], None],
    ) -> None:
        """Start ETW collection and deliver raw decoded records."""
        ...

    def stop(self) -> None:
        """Stop the ETW session and release its resources."""
        ...

    def get_health(self) -> CollectionHealth:
        """Report event loss, session status and errors."""
        ...
