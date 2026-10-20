import wmi
from .contracts import Device


class DeviceProvider:

    def __init__(self,host_id:str) -> None:
        self._wmi = wmi.WMI()
        self._host_id = host_id

    def list_devices(self) -> list[Device]:
        """Return discovered Windows storage devices/volumes."""
        devices = []
        for disk in self._wmi.Win32_DiskDrive():
            number = disk.Index
            device_id = f"disk:{number}"
            devices.append(
                Device(
                    host_id=self._host_id,
                    device_id=device_id,
                    display_name=disk.Caption or disk.DeviceID or device_id,
                    media_type=None,
                    capacity_bytes=(int(disk.Size) if disk.Size is not None else None),
                    free_bytes=None,
                    mount_points=[],
                    is_available=True,
                )
            )
        return devices

    def get_device(self, device_id: str) -> Device | None:
        """Look up a device by its canonical backend identity."""
        for device in self.list_devices():
            if device.device_id == device_id:
                return device
        return None
""" host_id: str
    device_id: str
    display_name: str
    media_type: MediaType | None
    capacity_bytes: int | None
    free_bytes: int | None
    mount_points: list[str]
    is_available: bool"""