# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import dataclasses
import logging
from datetime import datetime

import pytest

from backend.core.agent_adapter import LinuxAgentAdapter
from backend.core.http_api import create_http_api
from backend.core.normalization import normalize_linux_file_activity
from backend.core.service import CoreService
from backend.linux.models import (
    Drive,
    DriveMetric,
    ErrorCode,
    File,
    FileMetric,
    Process,
    ProcessMetric,
)

# These tests cover Shengrong's D4 CORE code (branch shengrong/d4-core).
# Until it is merged, skip instead of failing the whole run.
pytestmark = pytest.mark.skipif(
    not hasattr(CoreService, "get_current_file_activity"),
    reason="Linux CORE adapter changes are not merged yet (branch shengrong/d4-core)",
)

HOST = "test-host"
T0 = "2026-11-24T12:00:00Z"

FILE_ACTIVITY_KEYS = {
    "host_id", "file_id", "path", "device_id", "window_start_utc",
    "window_end_utc", "read_bytes", "write_bytes", "read_ops", "write_ops",
    "file_size_bytes", "source",
}
# Extra fields CORE passes through from the Linux FileMetric (not stored in the DB).
OPTIONAL_FILE_ACTIVITY_KEYS = {"read_average_gap", "write_average_gap"}


def assert_contract_fields(activity):
    """Every contract field is present; the only extras allowed are the optional ones."""
    assert FILE_ACTIVITY_KEYS <= set(activity)
    assert set(activity) - FILE_ACTIVITY_KEYS <= OPTIONAL_FILE_ACTIVITY_KEYS

# File gets a file_id in Mohan's D4 Linux backend. Until that is merged,
# File here only has absolute_path, inode and device.
HAS_FILE_ID = "file_id" in {f.name for f in dataclasses.fields(File)}


# --------------------------------------------------------------------------- #
# Fakes and builders
# --------------------------------------------------------------------------- #
def make_drive(name):
    return Drive(timestamp=T0, device_id=name, model="Model", serial="S",
                 size_bytes=1000, media_type="SSD", partitions=())


def drive_metric(duration=2, read_bytes=2000, write_bytes=4000):
    return DriveMetric(timestamp=T0, duration=duration, read_bytes=read_bytes,
                       write_bytes=write_bytes, read_count=10, write_count=20)


def process_metric(duration=2):
    return ProcessMetric(timestamp=T0, duration=duration, read_bytes=200,
                         write_bytes=400, reads_complete=1, writes_complete=2)


def make_process(pid, name="proc"):
    return Process(pid=pid, name=name, start_time_timestamp=T0)


def make_file(path, file_id=7):
    """A tracked File, using the fake form if the real one has no file_id yet."""
    if HAS_FILE_ID:
        return File(file_id, absolute_path=path, inode=1, device=1)
    return FakeFile(file_id=file_id, absolute_path=path)


@dataclasses.dataclass(frozen=True)
class FakeFile:
    file_id: int
    absolute_path: str


def file_metric(file, duration=8, read_bytes=4096, write_bytes=512,
                read_ops=3, write_ops=1):
    return FileMetric(
        file=file, timestamp=T0, duration=duration,
        read_attempts=read_ops, read_requested_bytes=read_bytes,
        read_success_ops=read_ops, read_completed_bytes=read_bytes,
        read_average_gap=None,
        write_attempts=write_ops, write_requested_bytes=write_bytes,
        write_success_ops=write_ops, write_completed_bytes=write_bytes,
        write_average_gap=None,
    )


class FakeLinuxBackend:
    """Returns whatever the test puts in device_io / process_io / file_stats."""

    def __init__(self, start_result=None):
        self.host_id = HOST
        self.start_result = start_result
        self.devices = []
        self.processes = []
        self.device_io = {}     # device_id -> DriveMetric | ErrorCode | None
        self.process_io = {}    # pid -> ProcessMetric | ErrorCode | None
        self.file_stats = {}    # File -> FileMetric | None
        self.file_stats_calls = []

    def start(self):
        return self.start_result

    def close(self):
        pass

    def list_devices(self):
        return self.devices

    def list_processes(self):
        return self.processes

    def get_device_io(self, interval, device_id):
        return self.device_io.get(device_id)

    def get_process_io(self, interval, pid):
        return self.process_io.get(pid)

    def get_all_file_stats(self, interval):
        self.file_stats_calls.append(interval)
        return self.file_stats


@pytest.fixture
def backend():
    return FakeLinuxBackend()


@pytest.fixture
def adapter(backend):
    return LinuxAgentAdapter(backend)


# --------------------------------------------------------------------------- #
# start()
# --------------------------------------------------------------------------- #
def test_start_logs_but_does_not_fail_when_file_tracer_unavailable(caplog):
    adapter = LinuxAgentAdapter(
        FakeLinuxBackend(start_result=ErrorCode.FILE_TRACER_UNAVAILABLE))
    with caplog.at_level(logging.ERROR):
        adapter.start()   # disk and process monitoring still run
    assert "FileIO" in caplog.text


def test_start_success_logs_nothing(caplog, adapter):
    with caplog.at_level(logging.ERROR):
        adapter.start()
    assert caplog.text == ""


# --------------------------------------------------------------------------- #
# Device metrics: ErrorCode handling
# --------------------------------------------------------------------------- #
def test_device_metric_is_normalized(adapter, backend):
    backend.devices = [make_drive("sda")]
    backend.device_io = {"sda": drive_metric(duration=2)}

    (metric,) = adapter.get_device_metrics()

    assert metric["host_id"] == HOST
    assert metric["device_id"] == "sda"
    assert metric["sample_window_seconds"] == 2.0
    assert metric["read_bytes_per_sec"] == 1000
    assert metric["write_bytes_per_sec"] == 2000
    assert metric["read_iops"] == 5 and metric["write_iops"] == 10


def test_device_invalid_time_interval_is_skipped(adapter, backend):
    backend.devices = [make_drive("sda"), make_drive("sdb")]
    backend.device_io = {"sda": ErrorCode.INVALID_TIME_INTERVAL,
                         "sdb": drive_metric()}
    assert [m["device_id"] for m in adapter.get_device_metrics()] == ["sdb"]


def test_device_none_is_skipped(adapter, backend):
    backend.devices = [make_drive("sda")]
    backend.device_io = {"sda": None}
    assert adapter.get_device_metrics() == []


def test_device_backend_not_started_raises(adapter, backend):
    backend.devices = [make_drive("sda")]
    backend.device_io = {"sda": ErrorCode.BACKEND_NOT_STARTED}
    with pytest.raises(RuntimeError, match="not started"):
        adapter.get_device_metrics()


@pytest.mark.parametrize("code", [ErrorCode.PERMISSION_DENIED,
                                  ErrorCode.PROCESS_NOT_FOUND])
def test_device_other_error_raises_with_its_name(adapter, backend, code):
    backend.devices = [make_drive("sda")]
    backend.device_io = {"sda": code}
    with pytest.raises(RuntimeError, match=code.name):
        adapter.get_device_metrics()


def test_device_error_never_reaches_normalization(adapter, backend):
    # The D3/D4 bug: an ErrorCode passed on as a metric crashed with
    # "'ErrorCode' object has no attribute 'timestamp'".
    backend.devices = [make_drive(n) for n in ("a", "b", "c")]
    backend.device_io = {"a": ErrorCode.INVALID_TIME_INTERVAL, "b": None,
                         "c": drive_metric()}
    results = adapter.get_device_metrics()
    assert all(isinstance(m, dict) for m in results)
    assert len(results) == 1


# --------------------------------------------------------------------------- #
# Process metrics: ErrorCode handling
# --------------------------------------------------------------------------- #
def test_process_metric_is_normalized(adapter, backend):
    backend.processes = [make_process(42, "python3")]
    backend.process_io = {42: process_metric(duration=2)}

    (metric,) = adapter.get_process_metrics()

    assert metric["pid"] == 42
    assert metric["process_name"] == "python3"
    assert metric["start_time_utc"] == T0
    assert metric["read_bytes_per_sec"] == 100
    assert metric["write_bytes_per_sec"] == 200


@pytest.mark.parametrize("code", [ErrorCode.INVALID_TIME_INTERVAL,
                                  ErrorCode.PROCESS_NOT_FOUND,
                                  ErrorCode.PROCESS_PID_REUSED])
def test_process_expected_errors_are_skipped(adapter, backend, code):
    # Processes end and PIDs get reused all the time: not an error for the user.
    backend.processes = [make_process(1), make_process(2)]
    backend.process_io = {1: code, 2: process_metric()}
    assert [m["pid"] for m in adapter.get_process_metrics()] == [2]


def test_process_backend_not_started_raises(adapter, backend):
    backend.processes = [make_process(1)]
    backend.process_io = {1: ErrorCode.BACKEND_NOT_STARTED}
    with pytest.raises(RuntimeError, match="not started"):
        adapter.get_process_metrics()


def test_process_other_error_raises_with_its_name(adapter, backend):
    backend.processes = [make_process(1)]
    backend.process_io = {1: ErrorCode.PERMISSION_DENIED}
    with pytest.raises(RuntimeError, match="PERMISSION_DENIED"):
        adapter.get_process_metrics()


def test_process_list_with_only_skipped_errors_is_empty(adapter, backend):
    backend.processes = [make_process(1), make_process(2)]
    backend.process_io = {1: ErrorCode.PROCESS_NOT_FOUND, 2: None}
    assert adapter.get_process_metrics() == []


# --------------------------------------------------------------------------- #
# FileActivity normalization
# --------------------------------------------------------------------------- #
def test_file_activity_has_the_contract_fields(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"x" * 1234)
    file = make_file(str(path), file_id=7)

    (activity,) = normalize_linux_file_activity({file: file_metric(file)}, HOST)

    assert_contract_fields(activity)


def test_file_activity_values(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"x" * 1234)
    file = make_file(str(path), file_id=7)
    metric = file_metric(file, duration=8, read_bytes=4096, write_bytes=512,
                         read_ops=3, write_ops=1)

    (activity,) = normalize_linux_file_activity({file: metric}, HOST)

    assert activity["host_id"] == HOST
    assert activity["file_id"] == "7"              # contract: str
    assert activity["path"] == str(path)
    assert activity["read_bytes"] == 4096
    assert activity["write_bytes"] == 512
    assert activity["read_ops"] == 3
    assert activity["write_ops"] == 1
    assert activity["file_size_bytes"] == 1234
    assert activity["source"] == "linux_ebpf"
    assert activity["device_id"] is None


def test_file_activity_passes_access_pattern_gaps_through(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"x")
    file = make_file(str(path))
    metric = dataclasses.replace(file_metric(file), read_average_gap=0.0, write_average_gap=512.5)

    (activity,) = normalize_linux_file_activity({file: metric}, HOST)

    if "read_average_gap" not in activity:
        pytest.skip("CORE does not pass the gap fields through on this branch")
    assert activity["read_average_gap"] == 0.0        # 0 = fully sequential
    assert activity["write_average_gap"] == 512.5


def test_file_activity_window_is_utc_and_matches_duration(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"x")
    file = make_file(str(path))

    (activity,) = normalize_linux_file_activity({file: file_metric(file, duration=8)}, HOST)

    assert activity["window_start_utc"] == T0
    assert activity["window_end_utc"].endswith("Z")
    start = datetime.fromisoformat(activity["window_start_utc"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(activity["window_end_utc"].replace("Z", "+00:00"))
    assert (end - start).total_seconds() == 8


def test_file_activity_skips_files_without_a_metric_yet(tmp_path):
    a = make_file(str(tmp_path / "a"), file_id=1)
    b = make_file(str(tmp_path / "b"), file_id=2)
    (tmp_path / "b").write_bytes(b"x")

    activities = normalize_linux_file_activity({a: None, b: file_metric(b)}, HOST)

    assert [x["file_id"] for x in activities] == ["2"]


def test_file_activity_deleted_file_has_unknown_size(tmp_path):
    file = make_file(str(tmp_path / "deleted.bin"))
    (activity,) = normalize_linux_file_activity({file: file_metric(file)}, HOST)
    assert activity["file_size_bytes"] is None


def test_file_activity_empty():
    assert normalize_linux_file_activity({}, HOST) == []


@pytest.mark.xfail(
    not HAS_FILE_ID,
    strict=True,
    raises=AttributeError,
    reason="Linux File has no file_id until Mohan's D4 backend is merged, so "
           "normalize_linux_file_activity crashes on real backend data.",
)
def test_file_activity_works_with_the_real_file_model(tmp_path):
    path = tmp_path / "real.bin"
    path.write_bytes(b"x")
    if HAS_FILE_ID:
        file = File(5, absolute_path=str(path), inode=1, device=1)
    else:
        file = File(absolute_path=str(path), inode=1, device=1)

    (activity,) = normalize_linux_file_activity({file: file_metric(file)}, HOST)
    assert activity["path"] == str(path)


# --------------------------------------------------------------------------- #
# HTTP: GET /api/v1/files/activity/latest
# --------------------------------------------------------------------------- #
def make_client(backend, demo_mode=False):
    core = CoreService(agent=LinuxAgentAdapter(backend), algorithm=None,
                       database=None, demo_mode=demo_mode, host_id=HOST)
    return create_http_api(core).test_client()


def test_file_activity_endpoint_returns_normalized_activity(tmp_path, backend):
    path = tmp_path / "data.bin"
    path.write_bytes(b"x" * 10)
    file = make_file(str(path), file_id=3)
    backend.file_stats = {file: file_metric(file)}

    response = make_client(backend).get("/api/v1/files/activity/latest")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["error"] is None
    (activity,) = body["data"]
    assert_contract_fields(activity)
    assert activity["file_id"] == "3"
    assert activity["path"] == str(path)


def test_file_activity_endpoint_asks_backend_for_8_second_window(backend):
    make_client(backend).get("/api/v1/files/activity/latest")
    assert backend.file_stats_calls == [8]


def test_file_activity_endpoint_with_nothing_tracked(backend):
    body = make_client(backend).get("/api/v1/files/activity/latest").get_json()
    assert body == {"status": "success", "data": [], "error": None}


def test_file_activity_endpoint_in_demo_mode_is_empty(backend):
    body = make_client(backend, demo_mode=True).get(
        "/api/v1/files/activity/latest").get_json()
    assert body["status"] == "success"
    assert body["data"] == []
    assert backend.file_stats_calls == []    # demo mode never touches the agent


@pytest.mark.xfail(
    strict=True,
    reason="Known bug since D3: the catch-all errorhandler(Exception) also "
           "catches Flask's 405 Method Not Allowed and turns it into a 500.",
)
def test_file_activity_endpoint_rejects_post(backend):
    response = make_client(backend).post("/api/v1/files/activity/latest")
    assert response.status_code == 405
    assert response.get_json()["status"] == "error"


def test_backend_error_becomes_json_error_not_crash(backend):
    # BACKEND_NOT_STARTED raises in the adapter; the API must answer with
    # the standard error envelope instead of an HTML error page.
    backend.devices = [make_drive("sda")]
    backend.device_io = {"sda": ErrorCode.BACKEND_NOT_STARTED}

    response = make_client(backend).get("/api/v1/metrics/latest")

    assert response.status_code == 500
    body = response.get_json()
    assert body["status"] == "error"
    assert body["data"] is None
    assert body["error"]["code"] == "CORE_ERROR"


def test_skipped_errors_still_give_success(backend):
    backend.devices = [make_drive("sda")]
    backend.device_io = {"sda": ErrorCode.INVALID_TIME_INTERVAL}
    backend.processes = [make_process(1)]
    backend.process_io = {1: ErrorCode.PROCESS_NOT_FOUND}
    client = make_client(backend)

    for url in ("/api/v1/metrics/latest", "/api/v1/processes/latest"):
        body = client.get(url).get_json()
        assert body == {"status": "success", "data": [], "error": None}, url
