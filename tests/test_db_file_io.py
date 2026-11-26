# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the D4 file I/O tables in the database (Sahil, branch db_file_io).

Covers:
  - file_subscriptions: upsert_file_subscription, list_file_subscriptions
  - file_move_records:  save_file_move_record, list_file_move_records,
                        get_incomplete_file_moves
  - file_activity:      query_file_activity_windows (newest first, with the
                        read/write average gap columns)
  - data still being there after WSD restarts (a new repository on the same file)
"""
import gc
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from backend.db import repository as repository_module
from backend.db.repository import SQLiteHistoryRepository

pytestmark = pytest.mark.skipif(
    not hasattr(SQLiteHistoryRepository, "save_file_move_record"),
    reason="file I/O database methods are not merged yet (branch db_file_io)",
)


# --------------------------------------------------------------------------- #
# Fixtures and helpers
# --------------------------------------------------------------------------- #
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_wsd.db")


@pytest.fixture
def repo(db_path):
    repository = SQLiteHistoryRepository(db_path=db_path)
    yield repository
    gc.collect()  # release SQLite handles so Windows can delete tmp_path


@pytest.fixture
def clock(monkeypatch):
    """Make the repository's "now" predictable: every call moves 1 second forward.

    The repository stamps updated_at_utc with datetime.now(); without this, two
    saves in the same clock tick (common on Windows) would have equal times and
    ordering tests would be flaky.
    """
    start = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)
    ticks = {"n": 0}

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            ticks["n"] += 1
            return start + timedelta(seconds=ticks["n"])

    monkeypatch.setattr(repository_module, "datetime", FakeDatetime)
    return ticks


def table_names(path):
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {name for (name,) in rows}
    finally:
        conn.close()


def subscription(path="/data/project", target_type="folder", **extra):
    sub = {"subscription_id": None, "host_id": "host-1", "path": path, "target_type": target_type}
    sub.update(extra)
    return sub


def move(move_id="move-1", **extra):
    record = {
        "move_id": move_id,
        "host_id": "host-1",
        "file_id": "file-7",
        "source_path": "/hdd/video.mkv",
        "target_path": "/ssd/video.mkv",
        "source_device_id": "sda",
        "target_device_id": "nvme0n1",
        "bytes_total": 1000,
    }
    record.update(extra)
    return record


def activity(path="/data/a.bin", device_id="sda", start="2026-11-25T12:00:00Z",
             end="2026-11-25T12:01:00Z", read_bytes=100):
    return {
        "host_id": "host-1", "file_id": "f-" + path, "path": path, "device_id": device_id,
        "window_start_utc": start, "window_end_utc": end,
        "read_bytes": read_bytes, "write_bytes": 10, "read_ops": 2, "write_ops": 1,
        "file_size_bytes": 4096, "read_average_gap": 0.0, "write_average_gap": 128.0,
        "source": "linux_ebpf",
    }


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #
def test_schema_creates_the_three_file_io_tables(repo, db_path):
    assert {"file_activity", "file_subscriptions", "file_move_records"} <= table_names(db_path)


def test_creating_the_repository_twice_keeps_existing_data(db_path):
    first = SQLiteHistoryRepository(db_path=db_path)
    first.upsert_file_subscription(subscription())
    second = SQLiteHistoryRepository(db_path=db_path)  # schema runs again
    assert len(second.list_file_subscriptions()) == 1
    del first, second
    gc.collect()


# --------------------------------------------------------------------------- #
# File subscriptions
# --------------------------------------------------------------------------- #
def test_no_subscriptions_gives_empty_list(repo):
    assert repo.list_file_subscriptions() == []


def test_new_subscription_is_saved_as_active(repo):
    repo.upsert_file_subscription(subscription("/data/project", "folder"))
    (row,) = repo.list_file_subscriptions()
    assert row["path"] == "/data/project"
    assert row["target_type"] == "folder"
    assert row["status"] == "active"
    assert row["host_id"] == "host-1"


def test_subscription_id_defaults_to_the_path(repo):
    repo.upsert_file_subscription(subscription("/data/a.txt", "file"))
    (row,) = repo.list_file_subscriptions()
    assert row["subscription_id"] == "/data/a.txt"


def test_explicit_subscription_id_is_kept(repo):
    repo.upsert_file_subscription(subscription("/data/a.txt", "file", subscription_id="sub-42"))
    (row,) = repo.list_file_subscriptions()
    assert row["subscription_id"] == "sub-42"


def test_same_path_again_updates_instead_of_duplicating(repo, clock):
    repo.upsert_file_subscription(subscription("/data/a.txt", "file"))
    repo.upsert_file_subscription(subscription("/data/a.txt", "file", status="removed"))
    rows = repo.list_file_subscriptions()
    assert len(rows) == 1
    assert rows[0]["status"] == "removed"


def test_update_keeps_created_time_but_changes_updated_time(repo, clock):
    repo.upsert_file_subscription(subscription("/data/a.txt", "file"))
    (before,) = repo.list_file_subscriptions()
    repo.upsert_file_subscription(subscription("/data/a.txt", "file", status="paused"))
    (after,) = repo.list_file_subscriptions()
    assert after["created_at_utc"] == before["created_at_utc"]
    assert after["updated_at_utc"] > before["updated_at_utc"]


def test_list_subscriptions_filters_by_status(repo):
    repo.upsert_file_subscription(subscription("/data/keep", "folder"))
    repo.upsert_file_subscription(subscription("/data/gone", "folder", status="removed"))
    active = repo.list_file_subscriptions(status="active")
    removed = repo.list_file_subscriptions(status="removed")
    assert [r["path"] for r in active] == ["/data/keep"]
    assert [r["path"] for r in removed] == ["/data/gone"]
    assert len(repo.list_file_subscriptions()) == 2


def test_subscriptions_are_listed_oldest_first(repo, clock):
    for path in ["/data/first", "/data/second", "/data/third"]:
        repo.upsert_file_subscription(subscription(path, "folder"))
    assert [r["path"] for r in repo.list_file_subscriptions()] == [
        "/data/first", "/data/second", "/data/third"]


def test_subscriptions_survive_a_restart(db_path):
    """Watched folders must come back after WSD restarts (the reason for the table)."""
    SQLiteHistoryRepository(db_path=db_path).upsert_file_subscription(subscription())
    gc.collect()
    restarted = SQLiteHistoryRepository(db_path=db_path)
    assert [r["path"] for r in restarted.list_file_subscriptions("active")] == ["/data/project"]
    del restarted
    gc.collect()


# --------------------------------------------------------------------------- #
# File move records
# --------------------------------------------------------------------------- #
def test_no_moves_gives_empty_lists(repo):
    assert repo.list_file_move_records() == []
    assert repo.get_incomplete_file_moves() == []


def test_new_move_defaults_to_pending_with_nothing_moved(repo):
    repo.save_file_move_record(move())
    (row,) = repo.list_file_move_records()
    assert row["status"] == "pending"
    assert row["bytes_moved"] == 0
    assert row["bytes_total"] == 1000
    assert row["source_path"] == "/hdd/video.mkv"
    assert row["target_path"] == "/ssd/video.mkv"
    assert row["error_message"] is None


def test_saving_the_same_move_again_updates_progress(repo, clock):
    repo.save_file_move_record(move(status="in_progress", bytes_moved=250,
                                    started_at_utc="2026-11-25T12:00:00Z"))
    repo.save_file_move_record(move(status="in_progress", bytes_moved=750))
    rows = repo.list_file_move_records()
    assert len(rows) == 1
    assert rows[0]["bytes_moved"] == 750
    assert rows[0]["status"] == "in_progress"


def test_progress_update_keeps_the_original_start_time(repo, clock):
    repo.save_file_move_record(move(status="in_progress", started_at_utc="2026-11-25T12:00:00Z"))
    repo.save_file_move_record(move(status="in_progress", bytes_moved=500))  # no start time
    (row,) = repo.list_file_move_records()
    assert row["started_at_utc"] == "2026-11-25T12:00:00Z"


def test_completed_move_records_completion(repo, clock):
    repo.save_file_move_record(move(status="in_progress", started_at_utc="2026-11-25T12:00:00Z"))
    repo.save_file_move_record(move(status="completed", bytes_moved=1000,
                                    completed_at_utc="2026-11-25T12:05:00Z"))
    (row,) = repo.list_file_move_records()
    assert row["status"] == "completed"
    assert row["bytes_moved"] == row["bytes_total"]
    assert row["completed_at_utc"] == "2026-11-25T12:05:00Z"


def test_failed_move_keeps_the_error_message(repo):
    repo.save_file_move_record(move(status="failed", error_message="Target disk is full"))
    (row,) = repo.list_file_move_records(status="failed")
    assert row["error_message"] == "Target disk is full"


@pytest.mark.parametrize("status", ["pending", "approved", "in_progress",
                                    "completed", "failed", "cancelled"])
def test_every_documented_status_can_be_saved(repo, status):
    repo.save_file_move_record(move(status=status))
    assert repo.list_file_move_records(status=status)[0]["status"] == status


def test_incomplete_moves_are_only_approved_and_in_progress(repo, clock):
    for status in ["pending", "approved", "in_progress", "completed", "failed", "cancelled"]:
        repo.save_file_move_record(move(move_id="move-" + status, status=status))
    incomplete = {row["move_id"] for row in repo.get_incomplete_file_moves()}
    assert incomplete == {"move-approved", "move-in_progress"}


def test_incomplete_moves_come_back_after_a_restart(db_path):
    """A move interrupted by a restart must be found again so it can resume."""
    SQLiteHistoryRepository(db_path=db_path).save_file_move_record(
        move(status="in_progress", bytes_moved=400))
    gc.collect()
    restarted = SQLiteHistoryRepository(db_path=db_path)
    (row,) = restarted.get_incomplete_file_moves()
    assert row["move_id"] == "move-1"
    assert row["bytes_moved"] == 400
    del restarted
    gc.collect()


def test_move_list_is_newest_first_and_respects_limit(repo, clock):
    for n in range(1, 6):
        repo.save_file_move_record(move(move_id=f"move-{n}"))
    rows = repo.list_file_move_records(limit=3)
    assert [r["move_id"] for r in rows] == ["move-5", "move-4", "move-3"]


def test_move_list_filters_by_status(repo):
    repo.save_file_move_record(move(move_id="a", status="completed"))
    repo.save_file_move_record(move(move_id="b", status="failed"))
    assert [r["move_id"] for r in repo.list_file_move_records(status="completed")] == ["a"]


def test_move_can_point_at_a_saved_recommendation(repo):
    repo.save_recommendations([{
        "recommendation_id": "rec-1", "mode": "raid0", "action": "move",
        "file_id": "file-7", "source_device_id": "sda", "target_device_id": "nvme0n1",
        "reason": "hot file", "created_at_utc": "2026-11-25T12:00:00Z",
    }])
    repo.save_file_move_record(move(recommendation_id="rec-1"))
    assert repo.list_file_move_records()[0]["recommendation_id"] == "rec-1"


def test_move_with_unknown_recommendation_is_rejected(repo):
    """Foreign keys are ON, so a move must refer to a recommendation that was saved.

    If CORE ever saves a move before (or without) its recommendation, this is
    the error it will get.
    """
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_file_move_record(move(recommendation_id="does-not-exist"))


# --------------------------------------------------------------------------- #
# File activity windows (used by recommendations: last 60 minutes of activity)
# --------------------------------------------------------------------------- #
def test_activity_windows_empty(repo):
    assert repo.query_file_activity_windows("2026-11-25T00:00:00Z", "2026-11-26T00:00:00Z") == []


def test_activity_windows_returns_saved_rows_with_all_columns(repo):
    repo.ingest_file_activity([activity()])
    (row,) = repo.query_file_activity_windows("2026-11-25T12:00:00Z", "2026-11-25T12:01:00Z")
    assert row == {key: value for key, value in activity().items()}


def test_activity_windows_includes_windows_that_overlap_the_range(repo):
    repo.ingest_file_activity([
        activity(path="/before", start="2026-11-25T10:00:00Z", end="2026-11-25T10:01:00Z"),
        activity(path="/overlap-start", start="2026-11-25T11:59:30Z", end="2026-11-25T12:00:30Z"),
        activity(path="/inside", start="2026-11-25T12:10:00Z", end="2026-11-25T12:11:00Z"),
        activity(path="/overlap-end", start="2026-11-25T12:59:30Z", end="2026-11-25T13:00:30Z"),
        activity(path="/after", start="2026-11-25T14:00:00Z", end="2026-11-25T14:01:00Z"),
    ])
    rows = repo.query_file_activity_windows("2026-11-25T12:00:00Z", "2026-11-25T13:00:00Z")
    assert [r["path"] for r in rows] == ["/overlap-end", "/inside", "/overlap-start"]  # newest first


def test_activity_windows_filter_by_path(repo):
    repo.ingest_file_activity([activity(path="/a"), activity(path="/b")])
    rows = repo.query_file_activity_windows("2026-11-25T00:00:00Z", "2026-11-26T00:00:00Z", path="/b")
    assert [r["path"] for r in rows] == ["/b"]


def test_activity_windows_filter_by_devices(repo):
    repo.ingest_file_activity([activity(path="/a", device_id="sda"),
                               activity(path="/b", device_id="sdb"),
                               activity(path="/c", device_id="nvme0n1")])
    rows = repo.query_file_activity_windows("2026-11-25T00:00:00Z", "2026-11-26T00:00:00Z",
                                            device_ids=["sda", "nvme0n1"])
    assert sorted(r["path"] for r in rows) == ["/a", "/c"]


def test_activity_windows_empty_device_list_means_no_filter(repo):
    repo.ingest_file_activity([activity(path="/a", device_id="sda"),
                               activity(path="/b", device_id=None)])
    rows = repo.query_file_activity_windows("2026-11-25T00:00:00Z", "2026-11-26T00:00:00Z",
                                            device_ids=[])
    assert len(rows) == 2


def test_activity_windows_newest_first_and_limit(repo):
    """Newest windows come first, so the limit keeps the most recent activity."""
    repo.ingest_file_activity([
        activity(path=f"/f{n}", start=f"2026-11-25T12:0{n}:00Z", end=f"2026-11-25T12:0{n}:59Z")
        for n in [3, 1, 2, 0]
    ])
    rows = repo.query_file_activity_windows("2026-11-25T12:00:00Z", "2026-11-25T13:00:00Z", limit=2)
    assert [r["path"] for r in rows] == ["/f3", "/f2"]


def test_activity_windows_full_order_is_newest_first(repo):
    repo.ingest_file_activity([
        activity(path=f"/f{n}", start=f"2026-11-25T12:0{n}:00Z", end=f"2026-11-25T12:0{n}:59Z")
        for n in [3, 1, 2, 0]
    ])
    rows = repo.query_file_activity_windows("2026-11-25T12:00:00Z", "2026-11-25T13:00:00Z")
    assert [r["path"] for r in rows] == ["/f3", "/f2", "/f1", "/f0"]


def test_activity_access_pattern_gaps_are_saved(repo):
    repo.ingest_file_activity([activity()])
    (row,) = repo.query_file_activity_windows("2026-11-25T00:00:00Z", "2026-11-26T00:00:00Z")
    assert row["read_average_gap"] == 0.0       # 0 = fully sequential reads
    assert row["write_average_gap"] == 128.0


def test_activity_without_gaps_is_saved_as_none(repo):
    """Windows activity has no gap fields; those rows must still be saved."""
    sample = activity()
    del sample["read_average_gap"], sample["write_average_gap"]
    repo.ingest_file_activity([sample])
    (row,) = repo.query_file_activity_windows("2026-11-25T00:00:00Z", "2026-11-26T00:00:00Z")
    assert row["read_average_gap"] is None
    assert row["write_average_gap"] is None


def test_activity_rows_without_device_are_kept(repo):
    """CORE sends device_id=None for Linux file activity for now (normalization TODO)."""
    repo.ingest_file_activity([activity(device_id=None)])
    (row,) = repo.query_file_activity_windows("2026-11-25T00:00:00Z", "2026-11-26T00:00:00Z")
    assert row["device_id"] is None
