
from .aggregation import EventAggregator
from .backend import WindowsBackend
from .contracts import (
    CollectionHealth,
    Device,
    DeviceMetric,
    FileActivity,
    ProcessMetric,
)
from .device_provider import DeviceProvider
from .etw_source import EtwDecoder, EtwSource
from .transport import EtwTransport


def create_backend(host_id: str) -> WindowsBackend:
    """Returns the windows backend fully wired up."""
    transport = EtwTransport()
    decoder = EtwDecoder()
    source = EtwSource(
        transport=transport,
        decoder=decoder,
    )
    device_provider = DeviceProvider(host_id)

    return WindowsBackend(
        host_id=host_id,
        etw_source=source,
        device_provider=device_provider,
    )


__all__ = [
    "create_backend",
    "WindowsBackend",
    "Device",
    "DeviceMetric",
    "ProcessMetric",
    "FileActivity",
    "CollectionHealth",
]
