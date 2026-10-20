"""US-02 integration test (QA): agent sample -> CORE -> DB -> CORE history query.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from backend.core.db_adapter import DataBaseAdaptor
from backend.core.service import CoreService

try:  # use Sahil's real database code once it is merged into main
    from backend.db.repository import SQLiteHistoryRepository
except ImportError:
    SQLiteHistoryRepository = None

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeAgent:
    """Stands in for the Windows/Linux agent, returning fixture data."""

    def __init__(self, devices, device_metrics, process_metrics):
        self.devices = devices
        self.device_metrics = device_metrics
        self.process_metrics = process_metrics

    def get_devices(self):
        return self.devices

    def get_device_metrics(self):
        return self.device_metrics

    def get_process_metrics(self):
        return self.process_metrics


class MockRepository:
    """In-memory stand-in for the DB (used until the real DB is merged).

    Follows the DB-01 contract: instance ID = pid_start, time range
    inclusive, results sorted by time, unknown values kept as None.
    """

    def __init__(self, db_path=None):
        self.rows = []

    def upsert_devices(self, devices):
        pass

    def ingest_device_metrics(self, samples):
        pass

    def ingest_process_metrics(self, samples):
        for s in samples:
            row = dict(s)
            row["process_instance_id"] = f"{s['pid']}_{s.get('start_time_utc')}"
            self.rows.append(row)

    def query_process_history(self, process_instance_ids, start_utc, end_utc, bucket_seconds=None):
        found = [dict(r) for r in self.rows
                 if r["process_instance_id"] in process_instance_ids
                 and start_utc <= r["timestamp_utc"] <= end_utc]
        return sorted(found, key=lambda r: r["timestamp_utc"])


Repository = SQLiteHistoryRepository or MockRepository


class US02HistoryFlowTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        repo = Repository(db_path=self.db_path)
        self.processes = load("metrics_process.json")
        self.agent = FakeAgent(load("devices.json"), load("metrics_device.json"), self.processes)
        self.core = CoreService(agent=self.agent, algorithm=None, database=DataBaseAdaptor(repo))

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def history_for(self, row):
        instance_id = f"{row['pid']}_{row['start_time_utc']}"
        return self.core.get_historical_process_activity(
            [instance_id], "2026-10-12T00:00:00Z", "2026-10-13T00:00:00Z")

    def test_recorded_sample_comes_back_unchanged(self):
        self.core.collect_and_record()
        game = self.processes[0]
        rows = self.history_for(game)
        self.assertEqual(len(rows), 1)
        for field in ("pid", "process_name", "timestamp_utc", "read_bytes_per_sec",
                      "write_bytes_per_sec", "attributed_device_id"):
            self.assertEqual(rows[0][field], game[field], field)

    def test_measured_zero_stays_zero(self):
        self.core.collect_and_record()
        self.assertEqual(self.history_for(self.processes[0])[0]["write_bytes_per_sec"], 0.0)

    def test_unknown_values_stay_null_not_zero(self):
        unknown = dict(self.processes[0], pid=6000,
                       read_bytes_per_sec=None, write_bytes_per_sec=None)
        self.agent.process_metrics = [unknown]
        self.core.collect_and_record()
        rows = self.history_for(unknown)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["read_bytes_per_sec"])
        self.assertIsNone(rows[0]["write_bytes_per_sec"])

    def test_no_data_returns_empty_list(self):
        self.assertEqual(self.history_for(self.processes[0]), [])

    def test_restarted_app_is_kept_separate(self):
        restarted = dict(self.processes[0], start_time_utc="2026-10-12T22:00:00Z",
                         timestamp_utc="2026-10-12T22:01:00Z")
        self.agent.process_metrics = [self.processes[0], restarted]
        self.core.collect_and_record()
        self.assertEqual(len(self.history_for(self.processes[0])), 1)
        self.assertEqual(len(self.history_for(restarted)), 1)

    def test_repeated_collection_builds_history_in_time_order(self):
        later = dict(self.processes[0], timestamp_utc="2026-10-12T21:00:01Z")
        self.agent.process_metrics = [self.processes[0]]
        self.core.collect_and_record()
        self.agent.process_metrics = [later]
        self.core.collect_and_record()
        times = [r["timestamp_utc"] for r in self.history_for(self.processes[0])]
        self.assertEqual(times, ["2026-10-12T21:00:00Z", "2026-10-12T21:00:01Z"])


if __name__ == "__main__":
    unittest.main()
