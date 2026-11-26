# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Regression checks for spatial freshness and public recommendation explanations."""
from datetime import datetime, timedelta
import json
from pathlib import Path

import pytest

from backend.algorithms.algo01 import prediction
from backend.algorithms.algo01.raid0_policy import evaluate_raid0_policy
from backend.algorithms.algo01.tests.test_prediction import (
    FILE_ID, HOST_ID, NOW, make_activity, make_hybrid_test_candidate,
)


def shift_activity(activity, seconds):
    for row in activity:
        for field in ("window_start_utc", "window_end_utc"):
            timestamp = datetime.fromisoformat(row[field])
            row[field] = (timestamp - timedelta(seconds=seconds)).isoformat()
    return activity


@pytest.mark.parametrize("strategy", ["latest", "average", "ml"])
def test_stale_spatial_history_does_not_boost_current_activity(monkeypatch, strategy):
    monkeypatch.setattr(prediction, "train_hybrid_predictor", lambda *_: (strategy, None))
    activity = shift_activity(make_activity([1200] * 5, gap=65536), 600)
    # The current 120-second record is valid for candidate selection, but cannot
    # supply the one-minute history needed by the predictor.
    activity.append({
        **activity[-1],
        "window_start_utc": (NOW - timedelta(seconds=120)).isoformat(),
        "window_end_utc": NOW.isoformat(),
        "read_ops": 2400,
        "read_average_gap": None,
    })
    result = prediction.apply_predictions(
        [make_hybrid_test_candidate()], activity, HOST_ID, NOW,
    )[0]

    assert result["prediction_strategy"] == "latest"
    assert result["spatial_factor"] == 1.0
    assert result["migration_score"] == 20.0


def test_fresh_missing_gaps_do_not_revive_older_measurements(monkeypatch):
    monkeypatch.setattr(prediction, "train_hybrid_predictor", lambda *_: ("latest", None))
    activity = shift_activity(make_activity([1200] * 3, gap=65536), 600)
    activity.extend(make_activity([1200] * 2))
    result = prediction.apply_predictions(
        [make_hybrid_test_candidate()], activity, HOST_ID, NOW,
    )[0]

    assert result["spatial_factor"] == 1.0
    assert result["migration_score"] == 20.0


@pytest.mark.parametrize("age, expected", [(0, 1.5), (60, 1.5), (61, 1.0), (-1, 1.0)])
def test_spatial_freshness_boundary(age, expected):
    history = prediction.prepare_file_history(make_activity([1200], gap=65536), HOST_ID, NOW)
    windows = history[FILE_ID]
    for window in windows:
        window["start"] -= timedelta(seconds=age)
        window["end"] -= timedelta(seconds=age)

    assert prediction.calculate_spatial_factor(windows, NOW) == pytest.approx(expected)


class FixedPredictor:
    def predict(self, features):
        return [7.0] * len(features)


@pytest.mark.parametrize("strategy,gap,is_mock,description,constraint", [
    pytest.param(
        "latest", None, False, "D2 read-activity heuristic.",
        "d2_read_activity_heuristic_unbenchmarked", id="latest",
    ),
    pytest.param(
        "latest", 65536, False, "Latest observed read rate with spatial scoring.",
        "d4_spatial_migration_heuristic_unbenchmarked", id="latest-spatial",
    ),
    pytest.param(
        "average", None, False, "Moving-average estimate for the next 10 minutes: 3 reads/s.",
        "d4_moving_average_migration_heuristic_unbenchmarked", id="moving-average",
    ),
    pytest.param(
        "average", 65536, False, "Moving-average estimate for the next 10 minutes: 3 reads/s.",
        "d4_moving_average_migration_heuristic_unbenchmarked", id="moving-average-spatial",
    ),
    pytest.param(
        "ml", None, False, "Predicted read rate for the next 10 minutes: 7 reads/s.",
        "d4_ml_migration_heuristic_unbenchmarked", id="ml",
    ),
    pytest.param(
        "ml", 65536, False, "Predicted read rate for the next 10 minutes: 7 reads/s.",
        "d4_ml_migration_heuristic_unbenchmarked", id="ml-spatial",
    ),
    pytest.param(
        "average", 65536, True, "D2 read-activity heuristic.",
        "d2_read_activity_heuristic_unbenchmarked", id="mock-average-fallback",
    ),
    pytest.param(
        "ml", 65536, True, "D2 read-activity heuristic.",
        "d2_read_activity_heuristic_unbenchmarked", id="mock-ml-fallback",
    ),
])
def test_public_recommendation_describes_actual_scoring(
    monkeypatch, strategy, gap, is_mock, description, constraint,
):
    # Force a host strategy to test the explanation independently of model fitting.
    model = FixedPredictor() if strategy == "ml" else None
    monkeypatch.setattr(prediction, "train_hybrid_predictor", lambda *_: (strategy, model))
    fixture = Path(__file__).parent / "fixtures/d2-temp-valid.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    source_device = payload["history"]["file_activity"][0]["device_id"]
    activity = make_activity([60, 120, 180, 240, 300], gap=gap)
    for row in activity:
        row["device_id"] = source_device
        if is_mock:
            row["source"] = "mock:regression"
    for device in payload["devices"]:
        device["host_id"] = HOST_ID
    payload["realtime"].update(host_id=HOST_ID, evaluation_time_utc=NOW.isoformat())
    payload["history"]["file_activity"] = activity

    records = evaluate_raid0_policy(**payload)
    result = records[0]
    assert result["action"] == "move"
    assert len(result) == 11
    assert result["estimated_benefit"] is None
    assert description in result["reason"]
    assert result["reason"].index(description) < result["reason"].index("Consider ")
    assert constraint in result["constraints"]
    if gap is not None and not is_mock:
        assert "Spatial factor: 1.5." in result["reason"]
    if is_mock:
        assert result["reason"].startswith("MOCK: ")
    if constraint != "d2_read_activity_heuristic_unbenchmarked":
        assert "D2 read-activity heuristic" not in result["reason"]
    assert evaluate_raid0_policy(**payload) == records
