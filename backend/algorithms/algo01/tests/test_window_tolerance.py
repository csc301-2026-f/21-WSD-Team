# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Allow small sampling jitter without hiding missing or overlapping history."""
from datetime import datetime, timedelta
import json
from pathlib import Path

import pytest

from backend.algorithms.algo01 import prediction
from backend.algorithms.algo01.inputs import is_window_duration_valid
from backend.algorithms.algo01.raid0_policy import evaluate_raid0_policy
from backend.algorithms.algo01.tests.test_prediction import (
    FILE_ID,
    HOST_ID,
    NOW,
    make_activity,
    make_hybrid_test_candidate,
)


def make_sampled_activity(count, interval=60.0, duration=60.0):
    """Model consecutive collector calls while keeping their real timestamps."""
    activity = make_activity([1200] * count, gap=65536)
    first_end = NOW - timedelta(seconds=interval * (count - 1))

    for index, row in enumerate(activity):
        end = first_end + timedelta(seconds=interval * index)
        start = end - timedelta(seconds=duration)
        row["window_start_utc"] = start.isoformat()
        row["window_end_utc"] = end.isoformat()

    return activity


def make_payload(activity):
    fixture = Path(__file__).parent / "fixtures/d2-temp-valid.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    source = payload["history"]["file_activity"][0]["device_id"]

    payload["realtime"].update(
        host_id=HOST_ID,
        evaluation_time_utc=NOW.isoformat(),
    )
    for device in payload["devices"]:
        device["host_id"] = HOST_ID

    payload["history"]["file_activity"] = [
        {**row, "device_id": source} for row in activity
    ]
    return payload


@pytest.mark.parametrize("duration, expected", [
    (0, False),
    (-1, False),
    (59.499999, False),
    (59.5, True),
    (59.998, True),
    (60.002, True),
    (60.5, True),
    (60.500001, False),
    (120, False),
])
def test_minute_window_duration_bounds(duration, expected):
    assert is_window_duration_valid(duration, 60, 60) is expected


@pytest.mark.parametrize("duration", [59.5, 59.998, 60.002, 60.5])
def test_history_uses_actual_duration_without_rounding(duration):
    activity = make_sampled_activity(1, duration=duration)
    original_start = activity[0]["window_start_utc"]
    original_end = activity[0]["window_end_utc"]
    history = prediction.prepare_file_history(activity, HOST_ID, NOW)
    window = history[FILE_ID][0]

    assert window["read_rate"] == pytest.approx(1200 / duration)
    assert window["start"] == datetime.fromisoformat(original_start)
    assert window["end"] == datetime.fromisoformat(original_end)
    assert activity[0]["window_start_utc"] == original_start
    assert activity[0]["window_end_utc"] == original_end


@pytest.mark.parametrize("interval", [59.5, 59.998, 60.002, 60.5])
def test_small_boundary_errors_still_produce_training_samples(interval):
    activity = make_sampled_activity(15, interval=interval)
    history = prediction.prepare_file_history(activity, HOST_ID, NOW)
    windows = history[FILE_ID]
    features, targets = prediction.build_training_samples(history)

    assert len(windows) == 15
    assert prediction.is_contiguous(windows)
    assert len(features) == 1
    assert targets == pytest.approx([20.0])


@pytest.mark.parametrize("interval", [59.998, 60.002])
def test_model_learns_from_jittered_history(interval):
    activity = make_sampled_activity(60, interval=interval)
    for index, row in enumerate(activity):
        row["read_ops"] = 1200 if (index + 1) % 10 == 0 else 0

    history = prediction.prepare_file_history(activity, HOST_ID, NOW)
    model = prediction.train_model(history, NOW)

    assert model is not None
    rate = prediction.predict_read_rate(model, history[FILE_ID], NOW)
    assert rate == pytest.approx(2.0, abs=0.1)


@pytest.mark.parametrize("interval", [1, 59.499999, 60.500001, 120])
def test_real_overlaps_or_missing_windows_cannot_train(interval):
    activity = make_sampled_activity(15, interval=interval)
    history = prediction.prepare_file_history(activity, HOST_ID, NOW)
    features, targets = prediction.build_training_samples(history)

    assert features == []
    assert targets == []
    if interval < 60:
        assert history[FILE_ID] == []
    else:
        assert not prediction.is_contiguous(history[FILE_ID])


@pytest.mark.parametrize("duration, action", [
    (59.499999, "none"),
    (59.5, "move"),
    (59.998, "move"),
    (60.002, "move"),
    (60.5, "move"),
    (60.500001, "none"),
])
def test_public_policy_applies_same_duration_tolerance(duration, action):
    activity = make_sampled_activity(1, duration=duration)
    payload = make_payload(activity)
    payload["mode_config"].update(
        min_window_seconds=60,
        max_window_seconds=60,
    )
    result = evaluate_raid0_policy(**payload)[0]

    assert result["action"] == action
    assert len(result) == 11


@pytest.mark.parametrize("interval", [59.998, 60.002])
def test_public_policy_keeps_average_strategy_with_jitter(
    monkeypatch, interval,
):
    monkeypatch.setattr(
        prediction,
        "train_hybrid_predictor",
        lambda *_: ("average", None),
    )
    payload = make_payload(make_sampled_activity(5, interval=interval))
    result = evaluate_raid0_policy(**payload)[0]

    assert result["action"] == "move"
    assert "Moving-average estimate" in result["reason"]
    assert "D2 read-activity heuristic" not in result["reason"]


@pytest.mark.parametrize("interval", [59.499999, 60.500001])
def test_broken_history_falls_back_without_filling_gaps(
    monkeypatch, interval,
):
    monkeypatch.setattr(
        prediction,
        "train_hybrid_predictor",
        lambda *_: ("average", None),
    )
    activity = make_sampled_activity(5, interval=interval)
    result = prediction.apply_predictions(
        [make_hybrid_test_candidate()], activity, HOST_ID, NOW,
    )[0]

    assert result["prediction_strategy"] == "latest"
    assert result["estimated_read_rate"] == 20.0
    assert result["predicted_read_rate"] is None


def test_jitter_does_not_mix_training_and_validation_periods():
    activity = make_sampled_activity(60, interval=60.002)
    history = prediction.prepare_file_history(activity, HOST_ID, NOW)
    training, validation = prediction.split_file_history(history, NOW)
    cutoff = NOW - timedelta(minutes=prediction.VALIDATION_WINDOWS)

    assert len(history[FILE_ID]) == 60
    assert all(window["end"] <= cutoff for window in training[FILE_ID])
    assert all(window["start"] >= cutoff for window in validation[FILE_ID])
    train_features, _ = prediction.build_training_samples(training)
    validation_features, _ = prediction.build_training_samples(validation)
    assert len(train_features) >= prediction.MIN_TRAINING_SAMPLES
    assert len(validation_features) >= prediction.MIN_VALIDATION_SAMPLES


def test_tolerance_does_not_admit_future_records():
    activity = make_sampled_activity(1)
    for field in ("window_start_utc", "window_end_utc"):
        timestamp = datetime.fromisoformat(activity[0][field])
        activity[0][field] = (
            timestamp + timedelta(seconds=0.002)
        ).isoformat()

    assert prediction.prepare_file_history(activity, HOST_ID, NOW) == {}
    result = evaluate_raid0_policy(**make_payload(activity))[0]
    assert result["action"] == "none"


@pytest.mark.parametrize("age, expected", [(60.002, 1.5), (60.5, 1.5)])
def test_spatial_freshness_uses_the_same_tolerance(age, expected):
    activity = make_sampled_activity(1)
    history = prediction.prepare_file_history(activity, HOST_ID, NOW)

    factor = prediction.calculate_spatial_factor(
        history[FILE_ID], NOW + timedelta(seconds=age),
    )
    assert factor == pytest.approx(expected)


class ConstantPredictor:
    def predict(self, features):
        return [7.0] * len(features)


@pytest.mark.parametrize("age", [60.002, 60.5])
@pytest.mark.parametrize("strategy", ["average", "ml"])
def test_prediction_freshness_uses_the_same_tolerance(age, strategy):
    history = prediction.prepare_file_history(
        make_sampled_activity(5), HOST_ID, NOW,
    )
    model = ConstantPredictor() if strategy == "ml" else None
    rate, actual_strategy = prediction.predict_hybrid_read_rate(
        strategy,
        model,
        history[FILE_ID],
        20.0,
        NOW + timedelta(seconds=age),
    )

    assert actual_strategy == strategy
    assert rate == pytest.approx(7.0 if strategy == "ml" else 20.0)
