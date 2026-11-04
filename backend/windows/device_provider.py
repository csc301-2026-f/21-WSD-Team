# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import wmi
import pythoncom
from .contracts import Device, MediaType


class DeviceProvider:

    def __init__(self,host_id:str) -> None:
        self._wmi =  wmi.WMI
        self._host_id = host_id

        #cache useful data to heavily reduce overhead, only place WMI is used
        pythoncom.CoInitialize()
        try:
            self._device_list = self._list_devices()
            self._drive_letter_mapping_bounds = self._get_drive_letter_mapping_bounds()
        finally: 
            pythoncom.CoUninitialize()

    def list_devices(self) -> list[Device]:
        """return cached discovered physical disks."""
        return self._device_list

    def _list_devices(self) -> list[Device]:
        """cache discovered physical disks and associated drive letters."""
        devices = []
        disks = self._wmi().Win32_DiskDrive()
        storage = self._wmi(namespace="root\\Microsoft\\Windows\\Storage").MSFT_PhysicalDisk()
        mount_points = self._disk_mount_points(disks)
        for disk in disks:
            number = disk.Index
            device_id = number
            media_type = "unknown"
            for storage_disk in storage:
                if int(storage_disk.DeviceID) == number:
                    media_type = self._get_media_type(storage_disk)
            free_space = 0
            for partition in self._get_partitions(disk):
                for logical_disk in self._get_logical_disks(partition):
                    space = int(logical_disk.FreeSpace)
                    if space == None:
                        print("maloc panic ^TM")
                        continue
                    free_space += space

            devices.append(
                Device(
                    host_id=self._host_id,
                    device_id=device_id,
                    display_name=(
                        disk.Caption or disk.DeviceID or f"disk:{number}"
                    ),
                    media_type=media_type,
                    capacity_bytes=(
                        int(disk.Size) if disk.Size is not None else None
                    ),
                    free_bytes=free_space,
                    mount_points=mount_points.get(number, []),
                    is_available=True,
                )
            )
        return devices    

    def _get_media_type(self, storage_disk) -> MediaType:
        """Find the type of a correlated storage disk"""
        try:
            bus_type = int(storage_disk.BusType)
            media_type = int(storage_disk.MediaType)
        except (AttributeError, TypeError, ValueError):
            return MediaType.UNKNOWN
        if bus_type == 17:
            return "nvme"
        match media_type:
            case 3:
                return "hdd"
            case 4:
                return "ssd"
            case 5:
                return "scm"
            case _:
                return "unknown" 


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

    def _disk_mount_points(self,disks) -> dict[int, list[str]]:
        """Map physical disk indexes to their logical drive letters."""
        result: dict[int, list[str]] = {}

        for disk in disks:
            disk_number = int(disk.Index)
            mount_points: set[str] = set()

            for partition in self._get_partitions(disk):
                for logical_disk in self._get_logical_disks(partition):
                    drive_letter = getattr(logical_disk, "DeviceID", None)
                    if drive_letter:
                        mount_points.add(str(drive_letter))

            result[disk_number] = sorted(mount_points)

        return result

    def _get_drive_letter_mapping_bounds(self) -> dict[int, list[(int,int,str)]]:
        """cache important information to map disk number and offset to drive letter."""
        disks = self._wmi().Win32_DiskDrive()
        mapping = {}
        for disk in disks:
            disk_number = disk.Index
            letter_bound_entries = []
            for partition in self._get_partitions(disk):
                try:
                    start = int(partition.StartingOffset)
                    size = int(partition.Size)
                except (TypeError, ValueError):
                    continue
                end = start + size
                for logical_disk in self._get_logical_disks(partition):
                    drive_letter = getattr(logical_disk, "DeviceID", None)
                    if drive_letter:
                        letter_bound_entries.append((start,end,str(drive_letter)))
            mapping[disk_number] = letter_bound_entries
        return mapping


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

        mapping = self._drive_letter_mapping_bounds
        offset_bounds = mapping.get(disk_number)
        if offset_bounds is None:
            return None
        count = 0
        found_letter = None
        for start, end, letter in offset_bounds:
            if not (start <= byte_offset < end): continue
            count += 1
            found_letter = letter
        if count != 1: return None
        return found_letter
        
            
