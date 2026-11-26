# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import dataclasses
import logging
import os

import pytest

from backend.core.agent_adapter import LinuxAgentAdapter
from backend.core.db_adapter import DataBaseAdaptor
from backend.core.http_api import create_http_api
from backend.core.service import CoreService
from backend.db.repository import SQLiteHistoryRepository
from backend.linux.models import ErrorCode

HOST = "test-host"
SUBSCRIPTIONS = "/api/v1/files/subscriptions"

# CoreService.track_file and friends only exist on Shengrong's D4 branch.
pytestmark = pytest.mark.skipif(
    not hasattr(CoreService, "track_file"),
    reason="file subscription code is not merged yet (branch shengrong/d4-core)",
)


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class FakeFile:
    """Stands in for backend.linux.models.File (only absolute_path is used here)."""
    absolute_path: str


class FakeTrackingBackend:
    """Fake Linux backend that tracks files in memory.

    Put an ErrorCode in `errors[method_name]` to make that call fail.
    """

    def __init__(self):
        self.host_id = HOST
        self.tracked = set()
        self.errors = {}
        self.file_stats = {}
        self.file_stats_calls = []

    def _error(self, name):
        return self.errors.get(name)

    def start(self):
        return None

    def close(self):
        pass

    def list_devices(self):
        return []

    def list_processes(self):
        return []

    def track_file(self, path):
        if self._error("track_file"):
            return self._error("track_file")
        file = FakeFile(path)
        self.tracked.add(file)
        return file

    def track_folder(self, path):
        if self._error("track_folder"):
            return self._error("track_folder")
        files = []
        for root, _dirs, names in os.walk(path):
            for name in sorted(names):
                file = FakeFile(os.path.join(root, name))
                self.tracked.add(file)
                files.append(file)
        return tuple(files)

    def untrack_file(self, file):
        if self._error("untrack_file"):
            return self._error("untrack_file")
        if file not in self.tracked:
            return ErrorCode.FILE_NOT_TRACKED
        self.tracked.discard(file)
        return None

    def untrack_folder(self, files):
        if self._error("untrack_folder"):
            return self._error("untrack_folder")
        missing = [f for f in files if f not in self.tracked]
        for file in files:
            self.tracked.discard(file)
        return ErrorCode.FILE_NOT_TRACKED if missing else None

    def list_tracked_files(self):
        return tuple(self.tracked)

    def get_all_file_stats(self, interval):
        self.file_stats_calls.append(interval)
        return self.file_stats


class FakeDatabase:
    """In-memory stand-in for the database adapter (same upsert-by-path rule as SQLite)."""

    def __init__(self):
        self.subscriptions = {}         # path -> row
        self.saved_activity = []
        self.activity_window_queries = []
        self.activity_to_return = []
        self.saved_recommendations = []

    def upsert_file_subscription(self, sub):
        row = dict(sub)
        row["subscription_id"] = sub.get("subscription_id") or sub["path"]
        row.setdefault("status", "active")
        self.subscriptions[sub["path"]] = row

    def list_file_subscriptions(self, status=None):
        rows = list(self.subscriptions.values())
        return [r for r in rows if status is None or r["status"] == status]

    def ingest_file_activity(self, samples):
        self.saved_activity.extend(samples)

    def query_file_activity_windows(self, start_utc, end_utc, path=None, device_ids=None, limit=5000):
        self.activity_window_queries.append((start_utc, end_utc))
        return self.activity_to_return

    def save_recommendations(self, items):
        self.saved_recommendations.extend(items)


class FakeAlgorithms:
    def __init__(self):
        self.calls = []

    def evaluate_raid0(self, devices, realtime, history, mode_config, capabilities):
        self.calls.append(("raid0", history))
        return [{"recommendation_id": "r-raid0"}]

    def evaluate_ssd(self, devices, realtime, history, mode_config, capabilities):
        self.calls.append(("ssd_caching", history))
        return [{"recommendation_id": "r-ssd"}]


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def backend():
    return FakeTrackingBackend()


@pytest.fixture
def adapter(backend):
    return LinuxAgentAdapter(backend)


@pytest.fixture
def database():
    return FakeDatabase()


@pytest.fixture
def algorithms():
    return FakeAlgorithms()


@pytest.fixture
def core(adapter, database, algorithms):
    return CoreService(adapter, algorithms, database, capabilities={}, host_id=HOST)


@pytest.fixture
def client(core):
    app = create_http_api(core)
    app.config["TESTING"] = False  # let the app's own error handlers answer, like in production
    return app.test_client()


@pytest.fixture
def a_file(tmp_path):
    path = tmp_path / "video.mkv"
    path.write_bytes(b"x" * 10)
    return str(path)


@pytest.fixture
def a_folder(tmp_path):
    folder = tmp_path / "project"
    (folder / "sub").mkdir(parents=True)
    (folder / "a.txt").write_text("a")
    (folder / "sub" / "b.txt").write_text("b")
    return str(folder)


def active_paths(database):
    return sorted(r["path"] for r in database.list_file_subscriptions("active"))


# --------------------------------------------------------------------------- #
# 1. LinuxAgentAdapter: tracking calls and their error codes
# --------------------------------------------------------------------------- #
def test_adapter_track_file_returns_the_backend_file(adapter):
    assert adapter.track_file("/data/a.txt") == FakeFile("/data/a.txt")


def test_adapter_track_folder_returns_every_file(adapter, a_folder):
    files = adapter.track_folder(a_folder)
    assert sorted(os.path.basename(f.absolute_path) for f in files) == ["a.txt", "b.txt"]


def test_adapter_list_tracked_files_passes_through(adapter):
    adapter.track_file("/data/a.txt")
    assert adapter.list_tracked_files() == (FakeFile("/data/a.txt"),)


@pytest.mark.parametrize("method, arg, code", [
    ("track_file", "/data/a.txt", ErrorCode.FILE_NOT_FOUND),
    ("track_file", "/data/a.txt", ErrorCode.PERMISSION_DENIED),
    ("track_file", "/data/a.txt", ErrorCode.TRACKING_LIMIT_REACHED),
    ("track_folder", "/data", ErrorCode.NOT_A_DIRECTORY),
    ("track_folder", "/data", ErrorCode.FILE_TRACER_UNAVAILABLE),
    ("untrack_file", FakeFile("/data/a.txt"), ErrorCode.FILE_NOT_TRACKED),
    ("untrack_folder", (FakeFile("/data/a.txt"),), ErrorCode.FILE_NOT_TRACKED),
])
def test_adapter_turns_error_codes_into_errors_with_the_code_name(adapter, backend, caplog,
                                                                  method, arg, code):
    backend.errors[method] = code
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match=code.name):
            getattr(adapter, method)(arg)
    assert code.name in caplog.text


def test_adapter_untrack_success_returns_none(adapter):
    file = adapter.track_file("/data/a.txt")
    assert adapter.untrack_file(file) is None


# --------------------------------------------------------------------------- #
# 2. CoreService: tracking is saved as a subscription in the database
# --------------------------------------------------------------------------- #
def test_track_file_saves_an_active_file_subscription(core, database):
    core.track_file("/data/a.txt")
    (row,) = database.list_file_subscriptions()
    assert row["path"] == os.path.normpath("/data/a.txt")
    assert row["target_type"] == "file"
    assert row["status"] == "active"
    assert row["host_id"] == HOST


def test_track_folder_saves_an_active_folder_subscription(core, database, a_folder):
    core.track_folder(a_folder)
    (row,) = database.list_file_subscriptions()
    assert row["path"] == os.path.normpath(a_folder)
    assert row["target_type"] == "folder"
    assert row["status"] == "active"


def test_subscription_paths_are_normalized(core, database, a_folder):
    core.track_folder(a_folder + os.sep)
    assert active_paths(database) == [os.path.normpath(a_folder)]


def test_untrack_file_marks_the_subscription_removed(core, database):
    file = core.track_file("/data/a.txt")
    core.untrack_file(file)
    (row,) = database.list_file_subscriptions()
    assert row["status"] == "removed"
    assert core.list_file_subscriptions() == []


def test_untrack_folder_marks_it_removed_and_forgets_it(core, database, a_folder):
    files = core.track_folder(a_folder)
    core.untrack_folder(files)
    assert database.list_file_subscriptions()[0]["status"] == "removed"
    assert core.track_folders == {}


def test_untrack_unknown_folder_raises(core):
    with pytest.raises(ValueError):
        core.untrack_folder((FakeFile("/never/tracked"),))


def test_list_subscriptions_shows_only_active_by_default(core):
    core.track_file("/data/keep.txt")
    core.untrack_file(core.track_file("/data/gone.txt"))
    assert [r["path"] for r in core.list_file_subscriptions()] == [os.path.normpath("/data/keep.txt")]


def test_failed_tracking_is_not_saved(core, backend, database):
    backend.errors["track_file"] = ErrorCode.PERMISSION_DENIED
    with pytest.raises(RuntimeError):
        core.track_file("/data/secret.txt")
    assert database.list_file_subscriptions() == []


def test_failed_untracking_keeps_the_subscription_active(core, backend, database):
    file = core.track_file("/data/a.txt")
    backend.errors["untrack_file"] = ErrorCode.FILE_NOT_TRACKED
    with pytest.raises(RuntimeError):
        core.untrack_file(file)
    assert database.list_file_subscriptions()[0]["status"] == "active"


# --------------------------------------------------------------------------- #
# 3. HTTP API: POST / DELETE / GET /api/v1/files/subscriptions
# --------------------------------------------------------------------------- #
def test_http_track_file(client, database, a_file):
    response = client.post(SUBSCRIPTIONS, json={"path": a_file})
    body = response.get_json()
    assert response.status_code == 200
    assert body == {"status": "success", "data": a_file, "error": None}
    assert active_paths(database) == [os.path.normpath(a_file)]


def test_http_track_folder(client, database, backend, a_folder):
    response = client.post(SUBSCRIPTIONS, json={"path": a_folder})
    assert response.get_json()["status"] == "success"
    assert active_paths(database) == [os.path.normpath(a_folder)]
    assert len(backend.tracked) == 2


def test_http_list_subscriptions(client, a_file, a_folder):
    client.post(SUBSCRIPTIONS, json={"path": a_file})
    client.post(SUBSCRIPTIONS, json={"path": a_folder})
    body = client.get(SUBSCRIPTIONS).get_json()
    assert body["status"] == "success"
    assert sorted((r["path"], r["target_type"]) for r in body["data"]) == sorted([
        (os.path.normpath(a_file), "file"), (os.path.normpath(a_folder), "folder")])


def test_http_list_subscriptions_empty(client):
    assert client.get(SUBSCRIPTIONS).get_json() == {"status": "success", "data": [], "error": None}


def test_http_untrack_file(client, database, a_file):
    client.post(SUBSCRIPTIONS, json={"path": a_file})
    response = client.delete(SUBSCRIPTIONS, json={"path": a_file})
    assert response.get_json() == {"status": "success", "data": a_file, "error": None}
    assert active_paths(database) == []
    assert client.get(SUBSCRIPTIONS).get_json()["data"] == []


def test_http_untrack_folder(client, database, backend, a_folder):
    client.post(SUBSCRIPTIONS, json={"path": a_folder})
    response = client.delete(SUBSCRIPTIONS, json={"path": a_folder})
    assert response.get_json()["status"] == "success"
    assert active_paths(database) == []
    assert backend.tracked == set()


def test_http_track_missing_path_gives_invalid_path(client, tmp_path):
    body = client.post(SUBSCRIPTIONS, json={"path": str(tmp_path / "nope")}).get_json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_PATH"


def test_http_untrack_missing_path_gives_invalid_path(client, tmp_path):
    body = client.delete(SUBSCRIPTIONS, json={"path": str(tmp_path / "nope")}).get_json()
    assert body["error"]["code"] == "INVALID_PATH"


def test_http_backend_error_is_a_json_error_not_a_crash(client, backend, a_file):
    backend.errors["track_file"] = ErrorCode.TRACKING_LIMIT_REACHED
    response = client.post(SUBSCRIPTIONS, json={"path": a_file})
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "CORE_ERROR"


@pytest.mark.xfail(strict=True, reason="INVALID_PATH is sent with HTTP 200; the contract says invalid requests are 4xx")
def test_http_track_missing_path_is_a_4xx(client, tmp_path):
    response = client.post(SUBSCRIPTIONS, json={"path": str(tmp_path / "nope")})
    assert 400 <= response.status_code < 500


@pytest.mark.xfail(strict=True, reason="no JSON body / no 'path' crashes (os.path.isfile(None)) and gives 500")
@pytest.mark.parametrize("kwargs", [{}, {"json": {}}, {"json": {"folder": "/tmp"}}])
def test_http_track_without_a_path_is_a_4xx(client, kwargs):
    response = client.post(SUBSCRIPTIONS, **kwargs)
    assert 400 <= response.status_code < 500


@pytest.mark.xfail(strict=True, reason="untracking an existing but untracked file hits file[0] on an empty list -> 500")
def test_http_untrack_file_that_was_never_tracked_is_a_4xx(client, a_file):
    response = client.delete(SUBSCRIPTIONS, json={"path": a_file})
    assert 400 <= response.status_code < 500


@pytest.mark.xfail(strict=True, reason="untracking an existing but untracked folder hits track_folders[path] -> KeyError -> 500")
def test_http_untrack_folder_that_was_never_tracked_is_a_4xx(client, a_folder):
    response = client.delete(SUBSCRIPTIONS, json={"path": a_folder})
    assert 400 <= response.status_code < 500


@pytest.mark.xfail(strict=True, reason="track_folders keys are normalized but DELETE looks up the raw path, "
                                       "so a trailing slash cannot be untracked")
def test_http_untrack_folder_with_trailing_slash(client, a_folder):
    client.post(SUBSCRIPTIONS, json={"path": a_folder + os.sep})
    response = client.delete(SUBSCRIPTIONS, json={"path": a_folder + os.sep})
    assert response.get_json()["status"] == "success"


@pytest.mark.xfail(strict=True, reason="a relative path reaches the backend (PATH_NOT_ABSOLUTE) and gives 500")
def test_http_track_relative_path_is_a_4xx(client, backend, tmp_path, monkeypatch):
    (tmp_path / "rel.txt").write_text("x")
    monkeypatch.chdir(tmp_path)
    backend.errors["track_file"] = ErrorCode.PATH_NOT_ABSOLUTE  # what the real Linux backend answers
    response = client.post(SUBSCRIPTIONS, json={"path": "rel.txt"})
    assert 400 <= response.status_code < 500


# --------------------------------------------------------------------------- #
# 4. Demo mode: there is no agent, so tracking is not supported
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason="demo mode has no agent (None), so tracking crashes with 500 "
                                       "instead of the contract's UNSUPPORTED error")
def test_http_track_in_demo_mode_is_unsupported(database, algorithms, a_file):
    demo = CoreService(None, algorithms, database, capabilities={}, demo_mode=True, host_id=HOST)
    client = create_http_api(demo).test_client()
    body = client.post(SUBSCRIPTIONS, json={"path": a_file}).get_json()
    assert body["error"]["code"] == "UNSUPPORTED"


# --------------------------------------------------------------------------- #
# 5. File activity is saved every minute and read back for recommendations
# --------------------------------------------------------------------------- #
def test_save_current_file_activity_asks_for_a_60_second_window(core, backend, database):
    core.save_current_file_activity()
    assert backend.file_stats_calls == [60]


def test_save_current_file_activity_does_nothing_in_demo_mode(database, algorithms):
    demo = CoreService(None, algorithms, database, capabilities={}, demo_mode=True, host_id=HOST)
    demo.save_current_file_activity()
    assert database.saved_activity == []


def test_recommendations_read_the_last_60_minutes_of_saved_activity(core, database, algorithms):
    from datetime import datetime
    database.activity_to_return = [{"path": "/data/hot.bin"}]
    core.refresh_recommendation()
    ((start, end),) = database.activity_window_queries
    to_dt = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    assert (to_dt(end) - to_dt(start)).total_seconds() == 3600
    assert start.endswith("Z") and end.endswith("Z")
    assert algorithms.calls[0][1] == {"file_activity": [{"path": "/data/hot.bin"}]}


# --------------------------------------------------------------------------- #
# 6. Mode switch: /api/v1/recommendations/refresh?mode=...
# --------------------------------------------------------------------------- #
def test_refresh_default_mode_uses_raid0(client, algorithms, database):
    body = client.post("/api/v1/recommendations/refresh").get_json()
    assert [name for name, _ in algorithms.calls] == ["raid0"]
    assert body["data"] == [{"recommendation_id": "r-raid0"}]
    assert database.saved_recommendations == [{"recommendation_id": "r-raid0"}]


def test_refresh_ssd_caching_mode_uses_algo02(client, algorithms, database):
    body = client.post("/api/v1/recommendations/refresh?mode=ssd_caching").get_json()
    assert [name for name, _ in algorithms.calls] == ["ssd_caching"]
    assert body["data"] == [{"recommendation_id": "r-ssd"}]
    assert database.saved_recommendations == [{"recommendation_id": "r-ssd"}]


# --------------------------------------------------------------------------- #
# 7. Move actions (HTTP-01k / HTTP-01l) - still being built
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason="execute_move_action is still 'pass' (returns None -> 500)")
def test_http_execute_action_answers_with_json(client):
    response = client.post("/api/v1/actions/execute", json={"recommendation_id": "r-1"})
    assert response.status_code != 500
    assert response.get_json()["status"] in {"success", "error"}


@pytest.mark.xfail(strict=True, reason="route is written '/api/v1/actions/{action_id}'; Flask needs "
                                       "'<action_id>', so real ids get 404")
def test_http_action_status_route_matches_an_id(client):
    response = client.get("/api/v1/actions/move-123")
    assert response.status_code != 404


# --------------------------------------------------------------------------- #
# 8. With the real database (runs once Sahil's db_file_io branch is merged)
# --------------------------------------------------------------------------- #
needs_db_branch = pytest.mark.skipif(
    not hasattr(SQLiteHistoryRepository, "upsert_file_subscription"),
    reason="file subscription tables are not merged yet (branch db_file_io)",
)


@pytest.fixture
def real_client(tmp_path, adapter, algorithms):
    import gc
    repository = SQLiteHistoryRepository(db_path=str(tmp_path / "wsd.db"))
    core = CoreService(adapter, algorithms, DataBaseAdaptor(repository), capabilities={}, host_id=HOST)
    yield create_http_api(core).test_client()
    gc.collect()


@needs_db_branch
def test_real_db_track_list_untrack_folder(real_client, a_folder):
    assert real_client.post(SUBSCRIPTIONS, json={"path": a_folder}).get_json()["status"] == "success"
    listed = real_client.get(SUBSCRIPTIONS).get_json()["data"]
    assert [(r["path"], r["target_type"], r["status"]) for r in listed] == [
        (os.path.normpath(a_folder), "folder", "active")]
    assert real_client.delete(SUBSCRIPTIONS, json={"path": a_folder}).get_json()["status"] == "success"
    assert real_client.get(SUBSCRIPTIONS).get_json()["data"] == []


@needs_db_branch
def test_real_db_track_same_file_twice_is_one_subscription(real_client, a_file):
    real_client.post(SUBSCRIPTIONS, json={"path": a_file})
    real_client.post(SUBSCRIPTIONS, json={"path": a_file})
    assert len(real_client.get(SUBSCRIPTIONS).get_json()["data"]) == 1


@needs_db_branch
def test_real_db_retrack_after_untrack_is_active_again(real_client, a_file):
    real_client.post(SUBSCRIPTIONS, json={"path": a_file})
    real_client.delete(SUBSCRIPTIONS, json={"path": a_file})
    real_client.post(SUBSCRIPTIONS, json={"path": a_file})
    (row,) = real_client.get(SUBSCRIPTIONS).get_json()["data"]
    assert row["status"] == "active"
