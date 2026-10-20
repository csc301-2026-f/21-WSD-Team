import os
import pytest
from backend.db.repository import SQLiteHistoryRepository

TEST_DB = "test_wsd.db"

@pytest.fixture
def repo():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    repository = SQLiteHistoryRepository(db_path=TEST_DB)
    yield repository
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_empty_query_returns_empty_list(repo):
    results = repo.query_device_history(
        device_ids=["sda1"],
        start_utc="2026-10-08T00:00:00Z",
        end_utc="2026-10-08T01:00:00Z"
    )
    assert results == []

def test_ingest_file_activity_safe_noop(repo):
    # Ensures Core will not hit an AttributeError when calling this method
    repo.ingest_file_activity([{"path": "/tmp/test.dat", "bytes": 1024}])
    assert repo.query_file_heat(start_utc="2026-10-08T00:00:00Z", end_utc="2026-10-08T01:00:00Z") == []

def test_process_history_raw_and_bucketed(repo):
    samples = [
        {
            "pid": 1420,
            "start_time_utc": "2026-10-08T20:00:00Z",
            "process_name": "blender",
            "timestamp_utc": "2026-10-08T20:00:10Z",
            "read_bytes_per_sec": 1000000.0,
            "write_bytes_per_sec": 2000000.0,
            "attributed_device_id": "nvme0n1"
        },
        {
            "pid": 1420,
            "start_time_utc": "2026-10-08T20:00:00Z",
            "process_name": "blender",
            "timestamp_utc": "2026-10-08T20:00:20Z",
            "read_bytes_per_sec": 3000000.0,
            "write_bytes_per_sec": 4000000.0,
            "attributed_device_id": "nvme0n1"
        }
    ]
    repo.ingest_process_metrics(samples)

    proc_id = "1420_2026-10-08T20:00:00Z"

    # Raw query
    raw = repo.query_process_history([proc_id], "2026-10-08T20:00:00Z", "2026-10-08T20:01:00Z")
    assert len(raw) == 2

    # Bucketed query
    bucketed = repo.query_process_history(
        [proc_id],
        "2026-10-08T20:00:00Z",
        "2026-10-08T20:01:00Z",
        bucket_seconds=60
    )
    assert len(bucketed) == 1
    assert bucketed[0]["sample_count"] == 2
    assert bucketed[0]["avg_read_bytes_per_sec"] == 2000000.0
    assert bucketed[0]["avg_write_bytes_per_sec"] == 3000000.0

def test_recommendation_upsert_updates_fields(repo):
    rec = [{
        "recommendation_id": "rec_100",
        "mode": "raid0",
        "action": "move",
        "reason": "high_io",
        "created_at_utc": "2026-10-08T20:00:00Z",
        "requires_approval": True,
        "estimated_benefit": {"iops_boost": 20},
        "constraints": []
    }]
    repo.save_recommendations(rec)

    # Upsert with altered approval & reason
    rec[0]["requires_approval"] = False
    rec[0]["reason"] = "user_override"
    repo.save_recommendations(rec)

    stored = repo.list_recommendations(mode="raid0")
    assert len(stored) == 1
    assert stored[0]["requires_approval"] is False
    assert stored[0]["reason"] == "user_override"

def test_ingest_and_query_device_metrics(repo):
    repo.upsert_devices([{"device_id": "nvme0n1", "display_name": "Main SSD"}])
    samples = [
        {
            "device_id": "nvme0n1",
            "timestamp_utc": "2026-10-08T20:00:10Z",
            "sample_window_seconds": 1.0,
            "read_bytes_per_sec": 50000000.0,
            "write_bytes_per_sec": 10000000.0,
            "read_iops": 1200.0,
            "write_iops": 300.0,
            "avg_read_latency_ms": 0.45,
            "avg_write_latency_ms": 0.80,
            "source": "os_agent"
        }
    ]
    repo.ingest_device_metrics(samples)

    # Query raw
    res = repo.query_device_history(
        device_ids=["nvme0n1"],
        start_utc="2026-10-08T20:00:00Z",
        end_utc="2026-10-08T20:01:00Z"
    )
    assert len(res) == 1
    assert res[0]["device_id"] == "nvme0n1"
    assert res[0]["read_iops"] == 1200.0