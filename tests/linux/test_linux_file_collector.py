# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import os
import pytest
from backend.linux.collector import FileIOCollector
from backend.linux.models import ErrorCode, File, FileCounters, FileMetric


class FakeProbe:
    """Stands in for file.FileIOProbe. Counters are set by the test."""

    def __init__(self):
        self.counters = {}   # slot -> FileCounters
        self.keys = {}       # kernel key -> slot
        self.closed = False

    def kernel_key(self, path):
        try:
            st = os.stat(path)
        except OSError:
            return None
        return (st.st_dev, st.st_ino, 0)

    def add(self, slot, key):
        self.keys[key] = slot

    def remove(self, key):
        self.keys.pop(key, None)

    def reset(self, slot):
        self.counters[slot] = FileCounters()

    def read(self, slot):
        return self.counters.get(slot, FileCounters())

    def close(self):
        self.closed = True

    def set_for(self, path, **values):
        st = os.stat(path)
        slot = self.keys[(st.st_dev, st.st_ino, 0)]
        self.counters[slot] = FileCounters(**values)


@pytest.fixture
def collector():
    """A started collector with a FakeProbe and no background sampling thread."""
    probe = FakeProbe()
    c = FileIOCollector(probe_factory=lambda: probe)
    c._fetch_data_loop = lambda: None   # sample() is called by the tests instead
    assert c.start() is None
    c.probe = probe
    yield c
    c.stop()


@pytest.fixture
def data_file(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"x" * 4096)
    return str(path)


# --------------------------------------------------------------------------- #
# Tracking
# --------------------------------------------------------------------------- #
def test_track_returns_file(collector, data_file):
    file = collector.track(data_file)
    assert isinstance(file, File)
    assert file.absolute_path == os.path.realpath(data_file)
    assert file.inode == os.stat(data_file).st_ino
    assert collector.tracked_files() == (file,)


def test_tracking_same_file_twice_gives_same_file(collector, data_file):
    first = collector.track(data_file)
    second = collector.track(data_file)
    assert first == second
    assert len(collector.tracked_files()) == 1


def test_untrack(collector, data_file):
    file = collector.track(data_file)
    assert collector.untrack(file) is None
    assert collector.tracked_files() == ()
    assert collector.untrack(file) == ErrorCode.FILE_NOT_TRACKED


def test_track_rejects_bad_paths(collector, tmp_path):
    assert collector.track("relative/path.bin") == ErrorCode.PATH_NOT_ABSOLUTE
    assert collector.track(str(tmp_path / "missing.bin")) == ErrorCode.FILE_NOT_FOUND
    assert collector.track(str(tmp_path)) == ErrorCode.NOT_A_REGULAR_FILE


def test_track_many_skips_bad_paths(collector, tmp_path):
    good = []
    for i in range(3):
        path = tmp_path / f"f{i}.bin"
        path.write_bytes(b"x")
        good.append(str(path))
    files = collector.track_many(good + [str(tmp_path / "missing.bin")])
    assert [f.absolute_path for f in files] == [os.path.realpath(p) for p in good]


def test_unavailable_tracer_is_reported(data_file):
    def broken_probe():
        raise RuntimeError("no BCC")

    c = FileIOCollector(probe_factory=broken_probe)
    assert c.start() == ErrorCode.FILE_TRACER_UNAVAILABLE
    assert c.track(data_file) == ErrorCode.FILE_TRACER_UNAVAILABLE


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def test_metric_is_none_until_two_samples(collector, data_file):
    file = collector.track(data_file)
    assert collector.get_metrics(1) == {file: None}
    collector.sample()
    assert collector.get_metrics(1) == {file: None}


def test_metric_is_difference_between_two_samples(collector, data_file):
    file = collector.track(data_file)
    collector.probe.set_for(data_file, read_attempts=2, read_completed_bytes=1000)
    collector.sample()
    collector.probe.set_for(data_file, read_attempts=7, read_completed_bytes=5096,
                            read_gap_sum=30, read_gap_count=3,
                            write_attempts=1, write_completed_bytes=512)
    collector.sample()

    metric = collector.get_metrics(1)[file]
    assert isinstance(metric, FileMetric)
    assert metric.read_attempts == 5
    assert metric.read_completed_bytes == 4096
    assert metric.read_average_gap == 10.0
    assert metric.write_attempts == 1
    assert metric.write_completed_bytes == 512
    assert metric.write_average_gap is None   # no write gaps measured
    assert metric.duration == 1


def test_untracked_file_disappears_from_metrics(collector, data_file):
    file = collector.track(data_file)
    collector.sample()
    collector.sample()
    collector.untrack(file)
    assert collector.get_metrics(1) == {}


def test_zero_interval_is_rejected(collector):
    with pytest.raises(ValueError):
        collector.get_metrics(0)


def test_replaced_file_keeps_being_tracked(collector, data_file, tmp_path):
    file = collector.track(data_file)
    collector.sample()

    # Editors and downloads often save by writing a new file and renaming it
    # over the old one, which gives the path a new inode.
    replacement = tmp_path / "data.bin.tmp"
    replacement.write_bytes(b"y" * 8192)
    os.replace(replacement, data_file)

    collector.sample()
    (tracked,) = collector.tracked_files()
    assert tracked.absolute_path == file.absolute_path
    assert tracked.inode == os.stat(data_file).st_ino   # follows the new file
