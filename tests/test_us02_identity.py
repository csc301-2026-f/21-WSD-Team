"""Regression checks for process-instance separation and evaluation time ordering."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
import time

from backend.windows.aggregation import EventAggregator
from backend.windows.contracts import RawIoEvent
from backend.core.service import CoreService
from backend.core.db_adapter import DataBaseAdaptor
from backend.db.repository import SQLiteHistoryRepository
from backend.core.http_api import create_http_api


def test_reused_pid_stays_separate_through_aggregation_database_and_http(tmp_path):
    aggregator = EventAggregator("host")
    end = time.time_ns()
    first_start = "2026-11-04T20:00:00Z"
    second_start = "2026-11-04T21:00:00Z"
    event = RawIoEvent(timestamp_ns=end-1000, operation="read", pid=123,
        process_start_time_utc=first_start, process_name="old.exe", device_id=0,
        transferred_bytes=4096, duration_ns=None, source="fileIO")
    aggregator.add_event(event)
    aggregator.add_event(replace(event, timestamp_ns=end, process_start_time_utc=second_start,
        process_name="new.exe", transferred_bytes=8192))
    # Unknown identities still serve file observation, but cannot form process history.
    aggregator.add_event(replace(event, process_start_time_utc=None, transferred_bytes=16384))
    rows = [asdict(r) for r in aggregator.process_metrics(60, end)]
    assert len(rows) == 2
    repo = SQLiteHistoryRepository(str(tmp_path/"identity.db"))
    repo.ingest_process_metrics(rows)
    core = CoreService(None, None, DataBaseAdaptor(repo))
    client = create_http_api(core).test_client()
    timestamp = rows[0]["timestamp_utc"]
    for started, expected, name in ((first_start, 4096/60, "old.exe"),
                                     (second_start, 8192/60, "new.exe")):
        response = client.get("/api/v1/processes/history", query_string={
            "process_instance_id": f"123_{started}", "start_utc": timestamp, "end_utc": timestamp})
        assert response.status_code == 200
        records = response.get_json()["data"]
        assert len(records) == 1
        assert records[0]["process_name"] == name
        assert records[0]["read_bytes_per_sec"] == expected
    assert repo.query_process_history(["123_None"], timestamp, timestamp) == []


def test_evaluation_time_is_after_file_collection():
    before = datetime(2026,11,4,20,tzinfo=timezone.utc)
    after = before + timedelta(seconds=10)
    clock = [before]
    activity = [{"window_end_utc": after.isoformat().replace("+00:00", "Z")}]
    def collect(seconds):
        clock[0] = after
        return activity
    captured = {}
    def evaluate(devices, realtime, history, mode_config, capabilities):
        captured.update(realtime=realtime, history=history)
        return []
    agent = SimpleNamespace(get_devices=lambda: [{"host_id": "host"}], get_file_activity=collect)
    core = CoreService(agent, SimpleNamespace(evaluate_raid0=evaluate),
        SimpleNamespace(save_recommendations=lambda rows: None))
    with patch("backend.core.service.datetime") as mocked:
        mocked.now.side_effect = lambda tz: clock[0]
        core.refresh_recommendation()
    assert captured["realtime"]["evaluation_time_utc"] == activity[0]["window_end_utc"]
