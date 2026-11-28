from datetime import timedelta

import numpy as np

from backend.algorithms.algo02 import prediction


def test_train_val_test_model_uses_chronological_partitions(monkeypatch, tmp_path):
    sample_count = 60
    y = np.array([index % 2 for index in range(sample_count)])
    X = np.array([
        [float(label), (index % 5) / 5, (index % 7) / 7, 0.25, 0.75]
        for index, label in enumerate(y)
    ])
    groups = np.array([f"file_{index % 10}" for index in range(sample_count)], dtype=object)
    ends = [prediction.datetime(2026, 1, 1) + timedelta(minutes=index) for index in range(sample_count)]
    monkeypatch.setattr(
        prediction,
        "build_sliding_window_dataset",
        lambda rows: (X, y, groups, ends),
    )
    model_path = tmp_path / "real-data-model.joblib"

    metrics = prediction.train_val_test_model([], model_path=model_path)

    assert metrics["train_samples"] == 42
    assert metrics["val_samples"] == 9
    assert metrics["test_samples"] == 9
    assert 0 <= metrics["val_f1"] <= 1
    assert 0 <= metrics["test_f1"] <= 1
    assert model_path.is_file()


def test_train_val_test_model_rejects_invalid_ratios():
    import pytest

    with pytest.raises(ValueError, match="sum to less than 1"):
        prediction.train_val_test_model([], train_ratio=0.8, val_ratio=0.2)
