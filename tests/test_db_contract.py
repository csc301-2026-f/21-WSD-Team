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