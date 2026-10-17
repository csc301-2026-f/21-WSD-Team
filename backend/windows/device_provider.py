#abstract for now, can't be wrong yet
from typing import Protocol

from .contracts import Device


class DeviceProvider(Protocol):
    def list_devices(self) -> list[Device]:
        """Return discovered Windows storage devices/volumes."""
        ...

    def get_device(self, device_id: str) -> Device | None:
        """Look up a device by its canonical backend identity."""
        ...
