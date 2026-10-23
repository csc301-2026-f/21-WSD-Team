import wmi
from .contracts import Device


class DeviceProvider:

    def __init__(self,host_id:str) -> None:
        self._wmi = wmi.WMI()
        self._host_id = host_id

    def list_devices(self) -> list[Device]:
        """Return discovered physical disks and associated drive letters."""
        mount_points = self._disk_mount_points()
        devices = []

        for disk in self._wmi.Win32_DiskDrive():
            number = disk.Index
            device_id = number

            devices.append(
                Device(
                    host_id=self._host_id,
                    device_id=device_id,
                    display_name=(
                        disk.Caption or disk.DeviceID or f"disk:{number}"
                    ),
                    media_type=None,
                    capacity_bytes=(
                        int(disk.Size) if disk.Size is not None else None
                    ),
                    free_bytes=None,
                    mount_points=mount_points.get(number, []),
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
    
    def _get_partitions(self, disk):
        """Return partitions associated with a physical disk."""
        return disk.associators(
            wmi_association_class="Win32_DiskDriveToDiskPartition",
            wmi_result_class="Win32_DiskPartition",
        )

    def _get_logical_disks(self, partition):
        """Return logical drives associated with a partition."""
        return partition.associators(
            wmi_association_class="Win32_LogicalDiskToPartition",
            wmi_result_class="Win32_LogicalDisk",
        )

    def _disk_mount_points(self) -> dict[int, list[str]]:
        """Map physical disk indexes to their logical drive letters."""
        result: dict[int, list[str]] = {}

        for disk in self._wmi.Win32_DiskDrive():
            disk_number = int(disk.Index)
            mount_points: set[str] = set()

            for partition in self._get_partitions(disk):
                for logical_disk in self._get_logical_disks(partition):
                    drive_letter = getattr(logical_disk, "DeviceID", None)
                    if drive_letter:
                        mount_points.add(str(drive_letter))

            result[disk_number] = sorted(mount_points)

        return result

    def resolve_drive_letter(
        self,
        disk_number: int,
        byte_offset: int,
    ) -> str | None:
        """
        Resolve a physical disk I/O offset to a logical drive letter.

        Requires DiskNumber and ByteOffset from a correlated DiskIo event.
        Returns None when the offset cannot be mapped unambiguously.
        """
        if disk_number < 0 or byte_offset < 0:
            return None

        for disk in self._wmi.Win32_DiskDrive():
            if int(disk.Index) != disk_number:
                continue

            matches: set[str] = set()

            for partition in self._get_partitions(disk):
                try:
                    start = int(partition.StartingOffset)
                    size = int(partition.Size)
                except (TypeError, ValueError):
                    continue

                if not (start <= byte_offset < start + size):
                    continue

                for logical_disk in self._get_logical_disks(partition):
                    drive_letter = getattr(logical_disk, "DeviceID", None)
                    if drive_letter:
                        matches.add(str(drive_letter))

            return next(iter(matches)) if len(matches) == 1 else None

        return None
