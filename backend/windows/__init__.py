# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only

from .contracts import (
    CollectionHealth,
    Device,
    DeviceMetric,
    FileActivity,
    ProcessMetric,
)



def create_backend(host_id: str):
    """Returns the windows backend fully wired up."""
    from .device_provider import DeviceProvider
    from .etw_source import EtwDecoder, EtwSource
    from .transport import EtwTransport
    from .backend import WindowsBackend
    from .file_operations import WindowsFileMover
    device_provider = DeviceProvider(host_id)
    file_mover = WindowsFileMover(device_provider=device_provider)
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
        file_mover=file_mover
    )


__all__ = [
    "create_backend",
    "Device",
    "DeviceMetric",
    "ProcessMetric",
    "FileActivity",
    "CollectionHealth",
]
