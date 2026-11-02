# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only

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
    device_provider = DeviceProvider(host_id)
    decoder = EtwDecoder(device_provider=device_provider)
    transport = EtwTransport()
    source = EtwSource(
        transport=transport,
        decoder=decoder,
    )
    

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
