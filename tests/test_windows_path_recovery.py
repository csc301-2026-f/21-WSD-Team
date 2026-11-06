# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Separate regressions for opening paths and late filename attribution."""
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.windows.aggregation import EventAggregator
from backend.windows.contracts import RawIoEvent
from dataclasses import replace
if sys.platform == "win32":
    from backend.windows.etw_source import EtwDecoder, EtwSource, FILE_IO_PROVIDER_GUID


NT_PATH = r"\Device\HarddiskVolume4\test.bin"
DOS_PATH = r"D:\test.bin"


def record(opcode, **fields):
    return {"EventHeader": {"ProviderId": FILE_IO_PROVIDER_GUID, "ProcessId": 123,
            "EventDescriptor": {"Opcode": opcode}}, **fields}


def decoder(**options):
    provider = SimpleNamespace(resolve_nt_file_path=lambda path: (DOS_PATH, 0) if path == NT_PATH else None)
    result = EtwDecoder(provider, **options)
    result._get_process_name = lambda pid: "test.exe"
    return result


def read(file_object="0x200"):
    return record(67, FileKey="0x100", FileObject=file_object, IoSize=4096)


@unittest.skipUnless(sys.platform == "win32", "Windows ETW dependencies required")
class TestWindowsPathRecovery(unittest.TestCase):
    def test_openpath_alone_resolves_the_opened_object(self):
        for enabled in (False, True):
            d = decoder(resolve_open_paths=enabled, recover_late_names=False)
            d.decode(record(64, FileObject="0x200", OpenPath=NT_PATH))
            event = d.decode(read())
            self.assertEqual(event.path, DOS_PATH if enabled else None)
            self.assertEqual(event.device_id, 0 if enabled else None)

    def test_late_name_updates_original_event_without_double_counting(self):
        for enabled in (False, True):
            d = decoder(resolve_open_paths=False, recover_late_names=enabled)
            aggregator = EventAggregator("host")
            original = d.decode(read())
            aggregator.add_event(original)
            d.decode(record(32, FileObject="0x100", FileName=NT_PATH))
            aggregator.resolve_file_events(d.take_resolved_events())
            with patch("backend.windows.aggregation.getsize", return_value=4194304):
                rows = aggregator.file_activity(60)
            self.assertEqual(len(rows), 1 if enabled else 0)
            snapshot = aggregator._snapshot(0, time.time_ns())
            self.assertEqual(len(snapshot), 1)
            self.assertEqual(snapshot[0].timestamp_ns, original.timestamp_ns)
            if enabled:
                self.assertEqual(rows[0].read_ops, 1)
                self.assertEqual(rows[0].read_bytes, 4096)
                self.assertEqual(snapshot[0].transferred_bytes, original.transferred_bytes)
                with patch("backend.windows.aggregation.getsize", return_value=4194304):
                    self.assertEqual(aggregator.file_activity(60)[0].read_ops, 1)

    def test_name_before_read_still_works(self):
        d = decoder()
        d.decode(record(0, FileObject="0x100", FileName=NT_PATH))
        self.assertEqual(d.decode(read()).path, DOS_PATH)
        self.assertEqual(d.take_resolved_events(), [])

    def test_reused_file_object_does_not_relabel_older_requests(self):
        d = decoder()
        original = d.decode(read())
        d.decode(record(64, FileObject="0x200", OpenPath=NT_PATH))
        d.decode(record(32, FileObject="0x100", FileName=NT_PATH))
        self.assertEqual(d.take_resolved_events(), [])
        self.assertIsNone(original.path)

    def test_unmapped_volume_and_expired_requests_are_not_guessed(self):
        d = decoder()
        d.decode(record(64, FileObject="0x200", OpenPath=r"\Device\Unknown\test.bin"))
        self.assertIsNone(d.decode(read()).path)
        with patch("backend.windows.etw_source.time_ns", return_value=time.time_ns() + 61_000_000_000):
            d.decode(record(32, FileObject="0x100", FileName=NT_PATH))
        self.assertEqual(d.take_resolved_events(), [])
        self.assertEqual(d.get_path_diagnostics()["pending_paths"], 0)

    def test_source_passes_attribution_updates_separately_from_io(self):
        records = [read(), record(32, FileObject="0x100", FileName=NT_PATH)]
        transport = SimpleNamespace(start=lambda callback: [callback(row) for row in records])
        source = EtwSource(transport, decoder())
        events, updates = [], []
        source.start(events.append, updates.extend)
        self.assertEqual(len(events), 1)
        self.assertEqual(len(updates), 1)
        self.assertIs(updates[0][0], events[0])
        self.assertEqual(updates[0][1].path, DOS_PATH)

    def test_unrelated_name_does_not_scan_other_pending_files(self):
        d = decoder()
        for key in range(10):
            d.decode(record(67, FileKey=key, FileObject=key+100, IoSize=4096))
        with patch.object(d._device_provider, "resolve_nt_file_path", return_value=None) as resolve:
            d.decode(record(32, FileObject="0xffff", FileName=NT_PATH))
        resolve.assert_not_called()
        self.assertEqual(d.get_path_diagnostics()["pending_paths"], 10)

    def test_same_object_with_different_paths_does_not_mix_activity(self):
        aggregator = EventAggregator("host")
        now = time.time_ns()
        for path, size in ((r"D:\first.bin", 4096), (r"D:\second.bin", 8192), (None, 16384)):
            aggregator.add_event(RawIoEvent(timestamp_ns=now, operation="read", pid=123,
                process_start_time_utc=None, process_name="test.exe", device_id=0,
                transferred_bytes=size, duration_ns=None, file_id=0x200, path=path,
                source="fileIO"))
        with patch("backend.windows.aggregation.getsize", return_value=4194304):
            rows = aggregator.file_activity(60)
        self.assertEqual({row.path: row.read_bytes for row in rows},
            {r"D:\first.bin": 4096, r"D:\second.bin": 8192})

    def test_read_and_write_handles_preserve_known_bytes_when_combined(self):
        aggregator = EventAggregator("host")
        event = RawIoEvent(timestamp_ns=time.time_ns(), operation="write", pid=123,
            process_start_time_utc=None, process_name="test.exe", device_id=0,
            transferred_bytes=4096, duration_ns=None, file_id=1, path=DOS_PATH, source="fileIO")
        aggregator.add_event(event)
        aggregator.add_event(replace(event, file_id=2, operation="read", transferred_bytes=4194304))
        with patch("backend.windows.aggregation.getsize", return_value=4194304):
            row = aggregator.file_activity(60)[0]
        self.assertEqual(row.read_bytes, 4194304)
        self.assertEqual(row.write_bytes, 4096)

    def test_unknown_bytes_on_an_actual_request_are_not_hidden(self):
        aggregator = EventAggregator("host")
        event = RawIoEvent(timestamp_ns=time.time_ns(), operation="read", pid=123,
            process_start_time_utc=None, process_name="test.exe", device_id=0,
            transferred_bytes=4096, duration_ns=None, file_id=1, path=DOS_PATH, source="fileIO")
        aggregator.add_event(event)
        aggregator.add_event(replace(event, file_id=2, transferred_bytes=None))
        with patch("backend.windows.aggregation.getsize", return_value=4194304):
            self.assertIsNone(aggregator.file_activity(60)[0].read_bytes)

    def test_process_identity_uses_verified_creation_time(self):
        d = decoder()
        process = SimpleNamespace(create_time=lambda: 1700000000.0,
                                  name=lambda: "test.exe", is_running=lambda: True)
        header = {"TimeStamp": 116444736000000000 + 1700000001 * 10000000}
        with patch("backend.windows.etw_source.psutil.Process", return_value=process):
            started, name = d._get_process_identity(123, header)
        self.assertEqual(started, "2023-11-14T22:13:20Z")
        self.assertEqual(name, "test.exe")

    def test_buffered_event_is_not_assigned_to_a_reused_pid(self):
        d = decoder()
        process = SimpleNamespace(create_time=lambda: 1700000002.0,
                                  name=lambda: "new.exe", is_running=lambda: True)
        header = {"TimeStamp": 116444736000000000 + 1700000001 * 10000000}
        with patch("backend.windows.etw_source.psutil.Process", return_value=process):
            self.assertEqual(d._get_process_identity(123, header), (None, None))

    def test_zero_missing_or_unreadable_process_times_are_not_fabricated(self):
        d = decoder()
        header = {"TimeStamp": 116444736000000000 + 1700000001 * 10000000}
        process = SimpleNamespace(create_time=lambda: 0.0)
        with patch("backend.windows.etw_source.psutil.Process", return_value=process):
            self.assertEqual(d._get_process_identity(4, header), (None, None))
        with patch("backend.windows.etw_source.psutil.Process", side_effect=OSError("denied")):
            self.assertEqual(d._get_process_identity(123, header), (None, None))
        self.assertEqual(d._get_process_identity(123, {}), (None, None))
        self.assertEqual(d._get_process_identity(123, {"TimeStamp": "bad"}), (None, None))


if __name__ == "__main__":
    unittest.main()
