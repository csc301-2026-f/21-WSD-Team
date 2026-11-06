import gc
import pytest
from backend.db.repository import SQLiteHistoryRepository


@pytest.fixture
def repo(tmp_path):
    # Each test gets its own temporary folder (cleaned up by pytest), so no
    # test_wsd.db / -wal / -shm files are left in the repo, and nothing has to
    # be deleted while SQLite still holds the file open (fails on Windows).
    repository = SQLiteHistoryRepository(db_path=str(tmp_path / "test_wsd.db"))
    yield repository
    gc.collect()


DEVICE = {"device_id": "nvme0n1", "display_name": "Main SSD", "media_type": "ssd"}

DEVICE_SAMPLE = {
    "device_id": "nvme0n1",
    "timestamp_utc": "2026-10-08T20:00:10Z",
    "sample_window_seconds": 1.0,
    "read_bytes_per_sec": 50_000_000.0,
    "write_bytes_per_sec": 10_000_000.0,
    "read_iops": 1200.0,
    "write_iops": 300.0,
    "avg_read_latency_ms": 0.45,
    "avg_write_latency_ms": 0.80,
    "source": "os_agent",
}

PROCESS_SAMPLE = {
    "pid": 1420,
    "start_time_utc": "2026-10-08T20:00:00Z",
    "process_name": "blender",
    "timestamp_utc": "2026-10-08T20:00:10Z",
    "read_bytes_per_sec": 1_000_000.0,
    "write_bytes_per_sec": 2_000_000.0,
    "attributed_device_id": "nvme0n1",
}

PROC_ID = "1420_2026-10-08T20:00:00Z"

RECOMMENDATION = {
    "recommendation_id": "rec_100",
    "mode": "raid0",
    "action": "move",
    "reason": "high_io",
    "created_at_utc": "2026-10-08T20:00:00Z",
    "requires_approval": True,
    "estimated_benefit": {"iops_boost": 20},
    "constraints": [],
}

# upsert_devices

def test_upsert_devices_inserts_new_device(repo):
    repo.upsert_devices([DEVICE])
    # Verify the device is reachable by ingesting a metric and querying it
    repo.ingest_device_metrics([DEVICE_SAMPLE])
    res = repo.query_device_history(
        device_ids=["nvme0n1"],
        start_utc="2026-10-08T20:00:00Z",
        end_utc="2026-10-08T20:01:00Z",
    )
    assert len(res) == 1

def test_upsert_devices_updates_on_conflict(repo):
    repo.upsert_devices([{**DEVICE, "display_name": "Old Name", "media_type": "hdd"}])
    repo.upsert_devices([{**DEVICE, "display_name": "New Name", "media_type": "ssd"}])
    # Metric query still works (device_id is stable) — the upsert didn't duplicate
    repo.ingest_device_metrics([DEVICE_SAMPLE])
    res = repo.query_device_history(
        device_ids=["nvme0n1"],
        start_utc="2026-10-08T20:00:00Z",
        end_utc="2026-10-08T20:01:00Z",
    )
    assert len(res) == 1  # still exactly one metric row, not duplicated

def test_upsert_devices_empty_list_is_noop(repo):
    repo.upsert_devices([])  # must not raise


# ingest_device_metrics / query_device_history

def test_empty_query_returns_empty_list(repo):
    results = repo.query_device_history(
        device_ids=["sda1"],
        start_utc="2026-10-08T00:00:00Z",
        end_utc="2026-10-08T01:00:00Z",
    )
    assert results == []

def test_query_device_history_no_device_ids_returns_empty(repo):
    repo.upsert_devices([DEVICE])
    repo.ingest_device_metrics([DEVICE_SAMPLE])
    assert repo.query_device_history([], "2026-10-08T00:00:00Z", "2026-10-08T23:59:59Z") == []

def test_ingest_and_query_device_metrics(repo):
    repo.upsert_devices([DEVICE])
    repo.ingest_device_metrics([DEVICE_SAMPLE])

    res = repo.query_device_history(
        device_ids=["nvme0n1"],
        start_utc="2026-10-08T20:00:00Z",
        end_utc="2026-10-08T20:01:00Z",
    )
    assert len(res) == 1
    assert res[0]["device_id"] == "nvme0n1"
    assert res[0]["read_iops"] == 1200.0

def test_ingest_device_metrics_empty_list_is_noop(repo):
    repo.ingest_device_metrics([])  # must not raise or insert anything
    assert repo.query_device_history(
        ["nvme0n1"], "2026-10-08T00:00:00Z", "2026-10-08T23:59:59Z"
    ) == []

def test_query_device_history_out_of_range_returns_empty(repo):
    repo.upsert_devices([DEVICE])
    repo.ingest_device_metrics([DEVICE_SAMPLE])  # timestamp: 20:00:10Z
    res = repo.query_device_history(
        device_ids=["nvme0n1"],
        start_utc="2026-10-08T21:00:00Z",  # after the sample
        end_utc="2026-10-08T22:00:00Z",
    )
    assert res == []

def test_query_device_history_bucketed(repo):
    repo.upsert_devices([DEVICE])
    sample_a = {**DEVICE_SAMPLE, "timestamp_utc": "2026-10-08T20:00:10Z",
                "read_iops": 1000.0, "write_iops": 200.0}
    sample_b = {**DEVICE_SAMPLE, "timestamp_utc": "2026-10-08T20:00:40Z",
                "read_iops": 2000.0, "write_iops": 400.0}
    repo.ingest_device_metrics([sample_a, sample_b])

    bucketed = repo.query_device_history(
        device_ids=["nvme0n1"],
        start_utc="2026-10-08T20:00:00Z",
        end_utc="2026-10-08T20:01:00Z",
        bucket_seconds=60,
    )
    assert len(bucketed) == 1
    assert bucketed[0]["sample_count"] == 2
    assert bucketed[0]["avg_read_iops"] == 1500.0
    assert bucketed[0]["avg_write_iops"] == 300.0
    assert bucketed[0]["timestamp_utc"].endswith("Z")



# ingest_process_metrics / query_process_history

def test_process_history_raw_and_bucketed(repo):
    samples = [
        PROCESS_SAMPLE,
        {**PROCESS_SAMPLE, "timestamp_utc": "2026-10-08T20:00:20Z",
         "read_bytes_per_sec": 3_000_000.0, "write_bytes_per_sec": 4_000_000.0},
    ]
    repo.ingest_process_metrics(samples)

    # Raw query
    raw = repo.query_process_history(
        [PROC_ID], "2026-10-08T20:00:00Z", "2026-10-08T20:01:00Z"
    )
    assert len(raw) == 2

    # Bucketed query
    bucketed = repo.query_process_history(
        [PROC_ID], "2026-10-08T20:00:00Z", "2026-10-08T20:01:00Z", bucket_seconds=60
    )
    assert len(bucketed) == 1
    assert bucketed[0]["sample_count"] == 2
    assert bucketed[0]["avg_read_bytes_per_sec"] == 2_000_000.0
    assert bucketed[0]["avg_write_bytes_per_sec"] == 3_000_000.0
    assert bucketed[0]["timestamp_utc"] == "2026-10-08T20:00:00Z"
    assert bucketed[0]["timestamp_utc"].endswith("Z")

def test_query_process_history_no_ids_returns_empty(repo):
    repo.ingest_process_metrics([PROCESS_SAMPLE])
    assert repo.query_process_history(
        [], "2026-10-08T20:00:00Z", "2026-10-08T20:01:00Z"
    ) == []

def test_query_process_history_out_of_range_returns_empty(repo):
    repo.ingest_process_metrics([PROCESS_SAMPLE])  # timestamp: 20:00:10Z
    res = repo.query_process_history(
        [PROC_ID], "2026-10-08T21:00:00Z", "2026-10-08T22:00:00Z"
    )
    assert res == []

def test_process_instance_id_built_from_pid_and_start_time(repo):
    # When no explicit process_instance_id is given the repo builds it as
    # "{pid}_{start_time_utc}" — verify the composite key round-trips correctly.
    repo.ingest_process_metrics([PROCESS_SAMPLE])
    rows = repo.query_process_history(
        [PROC_ID], "2026-10-08T20:00:00Z", "2026-10-08T20:01:00Z"
    )
    assert len(rows) == 1
    assert rows[0]["process_instance_id"] == PROC_ID
    assert rows[0]["pid"] == 1420
    assert rows[0]["process_name"] == "blender"


# ingest_file_activity / query_file_heat

def test_ingest_file_activity_safe_noop(repo):
    # Core must not hit an AttributeError when calling this method
    repo.ingest_file_activity([{"path": "/tmp/test.dat", "bytes": 1024}])
    assert repo.query_file_heat(
        start_utc="2026-10-08T00:00:00Z", end_utc="2026-10-08T01:00:00Z"
    ) == []

def test_query_file_heat_always_returns_empty_list(repo):
    # File-level tracking is intentionally unimplemented; the contract is []
    result = repo.query_file_heat(
        start_utc="2026-10-08T00:00:00Z",
        end_utc="2026-10-08T23:59:59Z",
        limit=50,
        device_ids=["nvme0n1"],
    )
    assert result == []


# save_settings / get_settings

def test_settings_roundtrip(repo):
    repo.save_settings({"theme": "dark", "auto_mode": True, "threshold": 0.75})
    settings = repo.get_settings()
    assert settings["theme"] == "dark"
    assert settings["auto_mode"] is True
    assert settings["threshold"] == 0.75

def test_settings_upsert_overwrites_existing_key(repo):
    repo.save_settings({"mode": "manual"})
    repo.save_settings({"mode": "auto"})
    assert repo.get_settings()["mode"] == "auto"

def test_get_settings_returns_empty_dict_when_nothing_saved(repo):
    assert repo.get_settings() == {}

def test_settings_preserves_json_types(repo):
    # Lists and nested dicts must survive a round-trip through JSON serialization
    repo.save_settings({"devices": ["sda", "nvme0n1"], "limits": {"iops": 500}})
    s = repo.get_settings()
    assert s["devices"] == ["sda", "nvme0n1"]
    assert s["limits"] == {"iops": 500}

# save_recommendations / list_recommendations

def test_recommendation_upsert_updates_fields(repo):
    repo.save_recommendations([RECOMMENDATION])

    updated = {**RECOMMENDATION, "requires_approval": False, "reason": "user_override"}
    repo.save_recommendations([updated])

    stored = repo.list_recommendations(mode="raid0")
    assert len(stored) == 1
    assert stored[0]["requires_approval"] is False
    assert stored[0]["reason"] == "user_override"

def test_list_recommendations_no_filter_returns_all(repo):
    rec_a = {**RECOMMENDATION, "recommendation_id": "rec_a", "mode": "raid0"}
    rec_b = {**RECOMMENDATION, "recommendation_id": "rec_b", "mode": "ssd_caching",
             "action": "cache"}
    repo.save_recommendations([rec_a, rec_b])
    all_recs = repo.list_recommendations()
    assert len(all_recs) == 2

def test_list_recommendations_mode_filter_isolates_correctly(repo):
    rec_a = {**RECOMMENDATION, "recommendation_id": "rec_a", "mode": "raid0"}
    rec_b = {**RECOMMENDATION, "recommendation_id": "rec_b", "mode": "ssd_caching",
             "action": "cache"}
    repo.save_recommendations([rec_a, rec_b])

    raid_recs = repo.list_recommendations(mode="raid0")
    assert len(raid_recs) == 1
    assert raid_recs[0]["mode"] == "raid0"

    ssd_recs = repo.list_recommendations(mode="ssd_caching")
    assert len(ssd_recs) == 1
    assert ssd_recs[0]["mode"] == "ssd_caching"

def test_list_recommendations_deserializes_json_fields(repo):
    repo.save_recommendations([RECOMMENDATION])
    stored = repo.list_recommendations()[0]
    # estimated_benefit and constraints must come back as Python objects, not raw JSON strings
    assert isinstance(stored["estimated_benefit"], dict)
    assert stored["estimated_benefit"]["iops_boost"] == 20
    assert isinstance(stored["constraints"], list)

def test_list_recommendations_requires_approval_is_bool(repo):
    repo.save_recommendations([RECOMMENDATION])  # requires_approval=True
    stored = repo.list_recommendations()[0]
    assert stored["requires_approval"] is True
    assert isinstance(stored["requires_approval"], bool)

def test_save_recommendations_empty_list_is_noop(repo):
    repo.save_recommendations([])  # must not raise
    assert repo.list_recommendations() == []
