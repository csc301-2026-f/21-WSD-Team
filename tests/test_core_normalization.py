import unittest

from backend.core.normalization import *
from backend.windows.contracts import *
from backend.linux.models import (Partition, Drive, Process, DriveMetric, ProcessMetric as LinuxProcessMetric)

class TestNormalization(unittest.TestCase):

    def test_size_to_bytes(self):
        result = size_to_bytes("10G")
        self.assertEqual(result, 10737418240)

    def test_normalize_windows_device(self):
        device = Device(host_id = "07650027-29ab-44b6-a851-292d58017c2c",
                        device_id = 0,
                        display_name = "Coat SSD",
                        media_type = "ssd",
                        capacity_bytes = 1145141919,
                        free_bytes = 10000000,
                        mount_points = ["C:"],
                        is_available = True
                        )
        result = normalize_windows_device([device])
        expected = [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                     "device_id": "0",
                     "display_name": "Coat SSD",
                     "media_type": "ssd",
                     "capacity_bytes": 1145141919,
                     "free_bytes": 10000000,
                     "mount_points": ["C:"],
                     "is_available": True
                     }]
        self.assertEqual(result, expected)

    def test_normalize_windows_device_metric(self):
        metric = DeviceMetric(host_id = "07650027-29ab-44b6-a851-292d58017c2c",
                              device_id = 0,
                              timestamp_utc = "2026-10-30T12:00:00Z",
                              sample_window_seconds = 10.0,
                              read_bytes_per_sec = 1000.0,
                              write_bytes_per_sec = 500.0,
                              read_iops = 20.0,
                              write_iops = 10.0,
                              avg_read_latency_ms = 2.5,
                              avg_write_latency_ms = 3.0,
                              source = "windows_etw"
                              )
        result = normalize_windows_device_metric([metric])
        expected = [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                    "device_id": "0",
                    "timestamp_utc": "2026-10-30T12:00:00Z",
                    "sample_window_seconds": 10.0,
                    "read_bytes_per_sec": 1000.0,
                    "write_bytes_per_sec": 500.0,
                    "read_iops": 20.0,
                    "write_iops": 10.0,
                    "avg_read_latency_ms": 2.5,
                    "avg_write_latency_ms": 3.0,
                    "source": "windows_etw"
                    }]
        self.assertEqual(result, expected)

    def test_normalize_windows_process_metric(self):
        metric = ProcessMetric(host_id = "07650027-29ab-44b6-a851-292d58017c2c",
                               pid = 114514,
                               start_time_utc = "2026-10-30T12:00:00Z",
                               process_name = "overwatch.exe",
                               timestamp_utc = "2026-10-30T12:00:00Z",
                               sample_window_seconds = 10.0,
                               read_bytes_per_sec = 1000.0,
                               write_bytes_per_sec = 500.0,
                               attributed_device_id = "0"
                               )
        result = normalize_windows_process_metric([metric])
        expected = [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                    "pid": 114514,
                    "start_time_utc": "2026-10-30T12:00:00Z",
                    "process_name": "overwatch.exe",
                    "timestamp_utc": "2026-10-30T12:00:00Z",
                    "sample_window_seconds": 10.0,
                    "read_bytes_per_sec": 1000.0,
                    "write_bytes_per_sec": 500.0,
                    "attributed_device_id": "0"
                    }]
        self.assertEqual(result, expected)

    def test_normalize_windows_process_metric_no_device(self):
        metric = ProcessMetric(host_id = "07650027-29ab-44b6-a851-292d58017c2c",
                               pid = 114514,
                               start_time_utc = "2026-10-30T12:00:00Z",
                               process_name = "overwatch.exe",
                               timestamp_utc = "2026-10-30T12:00:00Z",
                               sample_window_seconds = 10.0,
                               read_bytes_per_sec = 1000.0,
                               write_bytes_per_sec = 500.0,
                               attributed_device_id = None
                               )
        result = normalize_windows_process_metric([metric])
        expected = [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                     "pid": 114514,
                     "start_time_utc": "2026-10-30T12:00:00Z",
                     "process_name": "overwatch.exe",
                     "timestamp_utc": "2026-10-30T12:00:00Z",
                     "sample_window_seconds": 10.0,
                     "read_bytes_per_sec": 1000.0,
                     "write_bytes_per_sec": 500.0,
                     "attributed_device_id": None
                     }]
        self.assertEqual(result, expected)

    def test_normalize_windows_file_activity(self):
        activity = FileActivity(host_id = "07650027-29ab-44b6-a851-292d58017c2c",
                                file_id = "file-001",
                                path = "C:\\Users\\test\\example.txt",
                                device_id = 0,
                                window_start_utc = "2026-10-30T12:00:00Z",
                                window_end_utc = "2026-10-30T12:00:00Z",
                                read_bytes = 114514,
                                write_bytes = 1919,
                                read_ops = 10,
                                write_ops = 5,
                                file_size_bytes = 5000,
                                source = "window_etw"
                                )
        result = normalize_windows_file_activity([activity])
        expected = [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                    "file_id": "file-001",
                    "path": "C:\\Users\\test\\example.txt",
                    "device_id": "0",
                    "window_start_utc": "2026-10-30T12:00:00Z",
                    "window_end_utc": "2026-10-30T12:00:00Z",
                    "read_bytes": 114514,
                    "write_bytes": 1919,
                    "read_ops": 10,
                    "write_ops": 5,
                    "file_size_bytes": 5000,
                    "source": "window_etw"
                    }]
        self.assertEqual(result, expected)

    def test_normalize_windows_file_activity_no_device(self):
        activity = FileActivity(host_id = "07650027-29ab-44b6-a851-292d58017c2c",
                                file_id = "file-001",
                                path = "C:\\Users\\test\\example.txt",
                                device_id = None,
                                window_start_utc = "2026-10-30T12:00:00Z",
                                window_end_utc = "2026-10-30T12:00:00Z",
                                read_bytes = 114514,
                                write_bytes = 1919,
                                read_ops = 10,
                                write_ops = 5,
                                file_size_bytes = 5000,
                                source = "window_etw"
                                )
        result = normalize_windows_file_activity([activity])
        expected = [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                     "file_id": "file-001",
                     "path": "C:\\Users\\test\\example.txt",
                     "device_id": None,
                     "window_start_utc": "2026-10-30T12:00:00Z",
                     "window_end_utc": "2026-10-30T12:00:00Z",
                     "read_bytes": 114514,
                     "write_bytes": 1919,
                     "read_ops": 10,
                     "write_ops": 5,
                     "file_size_bytes": 5000,
                     "source": "window_etw"
                     }]
        self.assertEqual(result, expected)

    def test_normalize_linux_device(self):
        partition1 = Partition(name = "sda1",
                               size_bytes = 1000000000,
                               available_bytes = 10000000,
                               )
        partition2 = Partition(name = "sda2",
                               size_bytes = 1145141919,
                               available_bytes = 1919810
                               )
        device = Drive(timestamp = "2026-10-30T12:00:00Z",
                       device_id = "sda",
                       model = "Coat SSD",
                       serial = "1145141919",
                       size_bytes = 1145141919,
                       media_type = "SSD",
                       partitions = (partition1, partition2)
                       )
        result = normalize_linux_device([device], "07650027-29ab-44b6-a851-292d58017c2c")
        expected = [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                     "device_id": "sda",
                     "display_name": "Coat SSD",
                     "media_type": "ssd",
                     "capacity_bytes": 1145141919,
                     "free_bytes": 11919810,
                     "mount_points": [],
                     "is_available": True
                     }]
        self.assertEqual(result, expected)

    def test_normalize_linux_device_metrics(self):
        metric = DriveMetric(timestamp = "2026-10-30T12:00:00Z",
                             duration = 10,
                             read_bytes = 114514,
                             write_bytes = 1919,
                             read_count = 10,
                             write_count = 8,
                             )
        result = normalize_linux_device_metric([("sda", metric)],"07650027-29ab-44b6-a851-292d58017c2c")
        expected =  [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                      "device_id": "sda",
                      "timestamp_utc": "2026-10-30T12:00:00Z",
                      "sample_window_seconds": 10.0,
                      "read_bytes_per_sec": 11451.4,
                      "write_bytes_per_sec": 191.9,
                      "read_iops": 1.0,
                      "write_iops": 0.8,
                      "avg_read_latency_ms": None,
                      "avg_write_latency_ms": None,
                      "source": "/proc/diskstats"
                      }]
        self.assertEqual(result, expected)

    def test_normalize_linux_process_metrics(self):
        process = Process(pid = 114514,
                          name = "warthunder.exe",
                          start_time_timestamp = "2026-10-30T12:00:00Z"
                          )
        metric = LinuxProcessMetric(timestamp = "2026-10-30T12:00:00Z",
                                   duration = 10,
                                   read_bytes = 10000,
                                   write_bytes = 5000,
                                   reads_complete = 200,
                                   writes_complete = 100,
                                    )
        result = normalize_linux_process_metric([(process, metric)],
                                                "07650027-29ab-44b6-a851-292d58017c2c")
        expected = [{"host_id": "07650027-29ab-44b6-a851-292d58017c2c",
                     "pid": 114514,
                     "start_time_utc": "2026-10-30T12:00:00Z",
                     "process_name": "warthunder.exe",
                     "timestamp_utc": "2026-10-30T12:00:00Z",
                     "sample_window_seconds": 10.0,
                     "read_bytes_per_sec": 1000.0,
                     "write_bytes_per_sec": 500.0,
                     "attributed_device_id": None
                     }]
        self.assertEqual(result, expected)