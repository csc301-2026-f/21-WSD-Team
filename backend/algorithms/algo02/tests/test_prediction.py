# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""D4 ALGO-02 regression tests, adapted from the ALGO-01 test approach.

Place in backend/algorithms/algo02/tests/test_prediction.py (repo root cwd).
Run: python -m pytest backend/algorithms/algo02/tests/test_prediction.py -q
Requires pytest and scikit-learn (including NumPy and joblib).
All FileActivity is synthetic; no real files are moved or cached.
"""
from datetime import datetime, timedelta, timezone
from random import Random

import numpy as np
import pytest

from backend.algorithms.algo02 import prediction

HOST_ID = "test_host"
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def make_activity(read_counts, file_id="test_file", write_counts=None, interval=60):
    """Adapted from ALGO-01: generate one FileActivity row per minute."""
    if write_counts is None:
        write_counts = [0] * len(read_counts)
    assert len(read_counts) == len(write_counts)
    activity = []
    first_end = NOW - timedelta(seconds=interval * (len(read_counts) - 1))
    for i, (reads, writes) in enumerate(zip(read_counts, write_counts)):
        end = first_end + timedelta(seconds=i * interval)
        start = end - timedelta(seconds=60)
        activity.append({
            "host_id": HOST_ID,
            "file_id": file_id,
            "device_id": "hdd0",
            "path": f"/pool/{file_id}.bin",
            "window_start_utc": start.isoformat(),
            "window_end_utc": end.isoformat(),
            "read_ops": reads,
            "write_ops": writes,
            "read_bytes": reads * 4096,
            "write_bytes": writes * 4096,
            "file_size_bytes": 1024 * 1024,
            "read_average_gap": None,
            "write_average_gap": None,
            "source": "linux_ebpf",
        })
    return activity


@pytest.mark.parametrize("future_reads,future_writes,expected", [
    (2, 0, 1),  # 20 reads during next 10 minutes: cache
    (1, 0, 0),  # 10 reads: below the model's 15-read threshold
    (2, 1, 0),  # frequent reads but future writes: skip
])
def test_complete_training_window(future_reads, future_writes, expected):
    """Exactly one current minute plus ten complete future minutes."""
    activity = make_activity(
        [60] + [future_reads] * 10,
        write_counts=[0] + [future_writes] * 10,
    )
    X, y, groups, ends = prediction.build_sliding_window_dataset(activity)
    assert len(X) == len(y) == len(groups) == len(ends) == 1
    assert np.isfinite(X).all()
    assert y.tolist() == [expected]
    assert groups.tolist() == ["test_file"]
    assert ends == [NOW]


def test_incomplete_future_window():
    """Two future minutes cannot establish a ten-minute label."""
    X, y, groups, ends = prediction.build_sliding_window_dataset(
        make_activity([60, 60, 60])
    )
    assert len(X) == len(y) == len(groups) == len(ends) == 0


def test_missing_minute():
    """A missing record must not be treated as zero activity."""
    activity = make_activity([60] * 11)
    activity.pop(5)
    X, y, _, _ = prediction.build_sliding_window_dataset(activity)
    assert len(X) == len(y) == 0


def test_overlapping_windows():
    """One-minute collector windows sampled every second overlap heavily."""
    activity = make_activity([60] * 11, interval=1)
    X, y, _, _ = prediction.build_sliding_window_dataset(activity)
    assert len(X) == len(y) == 0


def test_duplicate_and_out_of_order_windows():
    """Duplicates and input ordering must not change labels or features."""
    activity = make_activity([60] + [1] * 10)
    original = prediction.build_sliding_window_dataset(activity)
    duplicate = activity + [activity[3].copy()] * 6
    Random(42).shuffle(duplicate)
    actual = prediction.build_sliding_window_dataset(duplicate)
    assert len(original[0]) == 1
    for expected_array, actual_array in zip(original[:3], actual[:3]):
        np.testing.assert_array_equal(actual_array, expected_array)
    assert actual[3] == original[3]
    assert actual[1].tolist() == [0]


def test_grid_search_uses_training_groups(monkeypatch, tmp_path):
    """Isolate the CV stage so a dataset-building bug cannot hide it."""
    X, y, groups, ends = [], [], [], []
    for minute in range(12):
        for group in range(6):
            label = (minute + group) % 2
            X.append([float(label), group / 6, minute / 12, 0.5, 0.5])
            y.append(label)
            groups.append(f"file_{group}")
            ends.append(NOW + timedelta(minutes=20 * minute))
    dataset = (np.array(X), np.array(y), np.array(groups, dtype=object), ends)
    monkeypatch.setattr(prediction, "build_sliding_window_dataset", lambda *a, **k: dataset)
    path = tmp_path / "cv.joblib"
    metrics = prediction.train_and_val_model([], model_path=path)
    assert metrics["train_samples"] == 54
    assert metrics["val_samples"] == 18
    assert path.is_file()
    assert 0 <= metrics["val_f1"] <= 1


def test_training_with_synthetic_file_activity(tmp_path):
    """Exercise dataset generation, fitting, validation, and model loading."""
    history = []
    for i in range(9):
        reads = [60 if i % 3 != 1 else 1] * 60
        writes = [5 if i % 3 == 2 else 0] * 60
        history.extend(make_activity(reads, f"file_{i}", writes))
    Random(42).shuffle(history)
    path = tmp_path / "trained.joblib"
    metrics = prediction.train_and_val_model(history, model_path=path)
    assert metrics["train_samples"] > 0
    assert metrics["val_samples"] > 0
    assert 0 <= metrics["val_accuracy"] <= 1
    assert 0 <= metrics["val_f1"] <= 1
    assert path.is_file()
    model = prediction.load_cache_model(path)
    assert set(model.classes_) == {0, 1}
    candidate = {
        "file_id": "file_0", "size": 1024 * 1024,
        "read_rate": 1.0, "read_ops": 60, "write_ops": 0,
        "read_bytes": 60 * 4096,
    }
    result = prediction.score_cache_candidates([candidate], history, model_path=path)
    assert len(result) == 1
    assert 0 <= result[0]["ml_cache_prob"] <= 1
    assert result[0]["predicted_future_reads"] >= 0


def test_insufficient_training_data_does_not_save_model(tmp_path):
    """An insufficient dataset must not produce a supposedly trained model."""
    path = tmp_path / "insufficient.joblib"
    with pytest.raises(ValueError):
        prediction.train_and_val_model(make_activity([60]), model_path=path)
    assert not path.exists()


def test_cold_start_scoring(tmp_path):
    """No saved model: the predictor should still return finite scores."""
    candidates = [
        {"file_id": "hot", "size": 1024 * 1024, "read_rate": 10.0,
         "read_ops": 600, "write_ops": 0, "read_bytes": 600 * 4096},
        {"file_id": "cold", "size": 1024 * 1024, "read_rate": 0.1,
         "read_ops": 6, "write_ops": 0, "read_bytes": 6 * 4096},
    ]
    path = tmp_path / "missing.joblib"
    scored = prediction.score_cache_candidates(candidates, [], model_path=path)
    assert {row["file_id"] for row in scored} == {"hot", "cold"}
    for row in scored:
        assert 0 <= row["ml_cache_prob"] <= 1
        assert np.isfinite(row["cache_value_density"])
        assert row["cache_value_density"] >= 0
    assert scored[0]["cache_value_density"] >= scored[1]["cache_value_density"]
    assert not path.exists()