# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only

"""Adaptive predictive file placement for ALGO-01."""

## Intuitive: Make prediction based on access freq &
#  condisder characteristic between SSD and HDD (optional)

from math import isfinite, log1p
from collections import defaultdict
from datetime import timedelta
from statistics import mean, pvariance, linear_regression

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error

from ..common.validation import parse_utc, is_integer, is_text, is_mock_source
from .inputs import SAMPLING_TOLERANCE_SECONDS, is_window_duration_valid


WINDOW_SECONDS = 60
FEATURE_WINDOWS = 5
PREDICTION_WINDOWS = 10
MAX_HISTORY_WINDOWS = 60

MIN_TRAINING_SAMPLES = 20
MIN_VALIDATION_SAMPLES = 5
VALIDATION_WINDOWS = 20
RIDGE_ALPHA = 1.0

SPATIAL_GAP_REFERENCE = 64 * 1024
SPATIAL_WEIGHT = 1.0

def validate_gap(gap):
    if gap is None:
        return None

    if isinstance(gap, bool):
        return None

    if not isinstance(gap, (int, float)):
        return None

    if not isfinite(gap) or gap < 0:
        return None

    return float(gap)

def prepare_file_history(activity, host_id, evaluation_time):
    """Prepare historical FileActivity for ML training."""

    grouped = defaultdict(list)

    history_seconds = WINDOW_SECONDS * MAX_HISTORY_WINDOWS
    cutoff = evaluation_time - timedelta(
        seconds=history_seconds + SAMPLING_TOLERANCE_SECONDS
    )

    for row in activity:

        if not isinstance(row, dict):
            continue

        if row.get("host_id") != host_id:
            continue

        if not is_text(row.get("file_id")):
            continue

        if not is_integer(row.get("read_ops")):
            continue

        if not is_integer(row.get("write_ops")):
            continue

        if not is_text(row.get("source")):
            continue

        if is_mock_source(row["source"]):
            continue

        try:
            start = parse_utc(row.get("window_start_utc"))
            end = parse_utc(row.get("window_end_utc"))
        except (ValueError, TypeError, OverflowError):
            continue

        duration = (end - start).total_seconds()

        if not is_window_duration_valid(
            duration, WINDOW_SECONDS, WINDOW_SECONDS
        ):
            continue

        if start < cutoff or end > evaluation_time:
            continue

        # Preserve real timestamps and compute rates from the actual duration.
        grouped[row["file_id"]].append({
            "start": start,
            "end": end,
            "read_rate": row["read_ops"] / duration,
            "write_rate": row["write_ops"] / duration,
            "read_average_gap": validate_gap(row.get("read_average_gap")),
            "write_average_gap": validate_gap(row.get("write_average_gap"))
        })

    cleaned_result = {}

    for file_id, windows in grouped.items():
        cleaned_result[file_id] = normalize_windows(windows)

    return cleaned_result

def normalize_windows(windows):
    unique = {}
    conflicts = set()

    # Deduplication
    for window in windows:
        key = (window["start"], window["end"])

        if key not in unique:
            unique[key] = window

        elif unique[key] != window:
            conflicts.add(key)

    #make sure time ordered
    ordered = sorted(unique.values(), key=lambda window: window["start"])

    overlapping, result = set(), []

    # Small overlaps are approximate samples, not exact cumulative counters.
    # Larger overlaps still invalidate both records.
    for i in range(1, len(ordered)):
        overlap = (
            ordered[i - 1]["end"] - ordered[i]["start"]
        ).total_seconds()
        if overlap > SAMPLING_TOLERANCE_SECONDS:
            overlapping.add(i - 1)
            overlapping.add(i)

    # exclue overlap detection
    for i, window in enumerate(ordered):
        if i in overlapping:
            continue

        key = (window["start"], window["end"])

        if key in conflicts:
            continue

        result.append(window)

    return result

def is_contiguous(windows):
    if not windows:
        return False

    for i in range(1, len(windows)):
        gap = (
            windows[i]["start"] - windows[i - 1]["end"]
        ).total_seconds()
        if abs(gap) > SAMPLING_TOLERANCE_SECONDS:
            return False

    return True

##### Data Preprocessing

def extract_spatial_features(windows):
    if not windows:
        return [0.0, 0.0, 0.0, 0.0]

    read_gaps = []
    write_gaps = []

    # collect available gap data only
    for window in windows:
        read_gap = window.get("read_average_gap")
        write_gap = window.get("write_average_gap")

        if read_gap is not None:
            read_gaps.append(log1p(read_gap))

        if write_gap is not None:
            write_gaps.append(log1p(write_gap))

    # calculate mean log gap to reduce the impact of large offsets
    mean_read_gap = 0.0
    mean_write_gap = 0.0

    if read_gaps:
        mean_read_gap = mean(read_gaps)

    if write_gaps:
        mean_write_gap = mean(write_gaps)

    # distinguish missing gap data from actual zero gap
    read_gap_availability = len(read_gaps) / len(windows)
    write_gap_availability = len(write_gaps) / len(windows)

    return [
        mean_read_gap,
        mean_write_gap,
        read_gap_availability,
        write_gap_availability
    ]

def extract_features(windows):
    """Extract temporal and spatial workload features."""

    # make sure we have enough continuous samples
    if len(windows) != FEATURE_WINDOWS:
        return None

    if not is_contiguous(windows):
        return None

    read_rates = []
    write_rates = []
    active_windows = 0

    # collect read/write rates and count active read windows
    for window in windows:
        read_rates.append(window["read_rate"])
        write_rates.append(window["write_rate"])

        if window["read_rate"] > 0:
            active_windows += 1

    # overall read activity and the latest read rate
    mean_read_rate = mean(read_rates)
    latest_read_rate = read_rates[-1]

    # measure how stable the read activity is
    read_rate_variance = pvariance(read_rates)

    # fit a linear trend using all historical read rates
    time_points = list(range(FEATURE_WINDOWS))

    trend_model = linear_regression(time_points, read_rates)

    read_rate_trend = trend_model.slope

    # distinguish persistent hot files from temporary hot files
    active_window_ratio = active_windows / FEATURE_WINDOWS

    # determine whether the workload is read-heavy
    total_reads = sum(read_rates)
    total_writes = sum(write_rates)
    total_ops = total_reads + total_writes

    read_fraction = 0.0

    if total_ops > 0:
        read_fraction = total_reads / total_ops

    # temporal locality and read/write behaviour
    features = [
        mean_read_rate,
        latest_read_rate,
        read_rate_variance,
        read_rate_trend,
        active_window_ratio,
        read_fraction
    ]

    # include spatial locality if available
    # missing gap data should not be treated as sequential IO
    spatial_features = extract_spatial_features(windows)

    features.extend(spatial_features)

    return features


##################################################################

#################### ML PERPARATION END ##########################

####SAMPLE DEALING

def build_training_samples(file_history):
    """Build training samples from historical FileActivity.
       Basically like a sliding window in TCP, where using some of
       data as training sample and others as test samples. And with moving window
       forward, test data will be training data, newer data into window will be test data
    """

    X_train = []
    y_train = []

    required_windows = FEATURE_WINDOWS + PREDICTION_WINDOWS

    # learn from historical workload of all monitored files
    for file_id, windows in file_history.items():

        # skip files without enough historical data
        if len(windows) < required_windows:
            continue

        # slide through the historical windows
        for i in range(len(windows) - required_windows + 1):

            sample = windows[i:i + required_windows]

            # make sure there are no missing windows
            if not is_contiguous(sample):
                continue

            # separate past observations and future activity
            feature_windows = sample[:FEATURE_WINDOWS]
            target_windows = sample[FEATURE_WINDOWS:]

            features = extract_features(feature_windows)

            if features is None:
                continue

            # calculate the actual future read rate
            future_read_rates = []

            for window in target_windows:
                future_read_rates.append(window["read_rate"])

            target_read_rate = mean(future_read_rates)

            # features as input, actual future read rate as label
            X_train.append(features)
            y_train.append(target_read_rate)

    return X_train, y_train

def split_file_history(file_history, evaluation_time):
    """Split historical windows into training and validation data."""

    training_history = defaultdict(list)
    validation_history = defaultdict(list)

    cutoff = evaluation_time - timedelta(
        seconds=VALIDATION_WINDOWS * WINDOW_SECONDS
    )

    # split by time instead of randomly splitting samples
    for file_id, windows in file_history.items():

        for window in windows:

            # historical data used for training
            if window["end"] <= cutoff:
                training_history[file_id].append(window)

            # recent data used for validation
            elif window["start"] >= cutoff:
                validation_history[file_id].append(window)

    return training_history, validation_history

####TRAINING

def train_model(file_history, evaluation_time):
    """Train and validate the workload prediction model, using ridge regression"""

    # split historical data to prevent data leakage
    training_history, validation_history = split_file_history(
        file_history, evaluation_time
    )

    X_train, y_train = build_training_samples(training_history)
    X_val, y_val = build_training_samples(validation_history)

    # fallback if there is not enough historical data
    if len(X_train) < MIN_TRAINING_SAMPLES:
        return None

    if len(X_val) < MIN_VALIDATION_SAMPLES:
        return None

    # normalize features before applying Ridge regression
    model = make_pipeline(
        StandardScaler(),
        Ridge(alpha=RIDGE_ALPHA)
    )

    # learn feature weights from historical workload
    model.fit(X_train, y_train)

    # predict future read rates on unseen historical samples
    predictions = model.predict(X_val)

    ml_predictions = []
    baseline_predictions = []

    for i in range(len(X_val)):

        # negative read rates are physically meaningless
        ml_predictions.append(max(0.0, predictions[i]))

        # D3 baseline: use the latest observed read rate
        baseline_predictions.append(X_val[i][1])

    # compare ML against the original D3 approach
    ml_error = mean_absolute_error(y_val, ml_predictions)
    baseline_error = mean_absolute_error(y_val, baseline_predictions)

    # fallback if ML does not improve prediction accuracy
    if ml_error >= baseline_error:
        return None

    # retrain using all available history after validation
    X_all, y_all = build_training_samples(file_history)

    model.fit(X_all, y_all)

    return model


#### PREDICRTION

def predict_read_rate(model, windows, evaluation_time):
    """Predict the average read rate for the next 10 minutes."""

    # fallback if the model is unavailable
    if model is None:
        return None

    if len(windows) < FEATURE_WINDOWS:
        return None

    # use the latest 5 windows for prediction
    recent_windows = windows[-FEATURE_WINDOWS:]

    # make sure the latest activity is not outdated
    age = (evaluation_time - recent_windows[-1]["end"]).total_seconds()

    if age < 0 or age > WINDOW_SECONDS + SAMPLING_TOLERANCE_SECONDS:
        return None

    # extract features from recent workload
    features = extract_features(recent_windows)

    if features is None:
        return None

    # sklearn expects a 2D feature array
    prediction = float(model.predict([features])[0])

    if not isfinite(prediction):
        return None

    # read rate cannot be negative
    return max(0.0, prediction)


def calculate_migration_score(predicted_read_rate, windows):
    """Estimate migration benefit using read hotness and spatial locality."""

    if predicted_read_rate is None:
        return None

    read_gaps = []

    # collect recent spatial locality information
    recent_windows = windows[-FEATURE_WINDOWS:]

    for window in recent_windows:
        gap = window.get("read_average_gap")

        if gap is not None:
            read_gaps.append(gap)

    # neutral factor if spatial information is unavailable
    spatial_factor = 1.0

    if read_gaps:
        average_gap = mean(read_gaps)

        # limit the impact of large gaps on migration decisions
        spatial_factor += SPATIAL_WEIGHT * (
            average_gap / (average_gap + SPATIAL_GAP_REFERENCE)
        )

    # predicted hotness adjusted by non-sequential access behaviour
    migration_score = predicted_read_rate * spatial_factor

    return migration_score


def calculate_spatial_factor(windows, evaluation_time):
    """Use spatial observations from the latest five minutes, if still current."""
    if not windows:
        return 1.0

    recent_windows = windows[-FEATURE_WINDOWS:]
    age = (evaluation_time - recent_windows[-1]["end"]).total_seconds()
    if age < 0 or age > WINDOW_SECONDS + SAMPLING_TOLERANCE_SECONDS:
        return 1.0

    spatial_seconds = FEATURE_WINDOWS * WINDOW_SECONDS
    cutoff = evaluation_time - timedelta(
        seconds=spatial_seconds + SAMPLING_TOLERANCE_SECONDS
    )
    # A fresh record with no gap must not revive older spatial measurements.
    spatial_windows = [
        window for window in recent_windows
        if window["start"] >= cutoff and window["end"] <= evaluation_time
    ]
    return calculate_migration_score(1.0, spatial_windows)

#####APPLY

def apply_predictions_legacy(candidates, activity, host_id, evaluation_time):
    """Preserve the original D4 scoring strategy for benchmark comparisons."""

    if not candidates:
        return candidates

    # prepare historical data and train one model for this host
    file_history = prepare_file_history(
        activity, host_id, evaluation_time
    )

    model = train_model(file_history, evaluation_time)

    # keep the original D3 behaviour if ML is unavailable
    if model is None:
        return candidates

    result = []

    for row in candidates:
        candidate = row.copy()

        # preserve observed read rate for fallback
        candidate["predicted_read_rate"] = None
        candidate["migration_score"] = row["read_rate"]

        # do not apply real workload predictions to mock data
        if row["is_mock"]:
            result.append(candidate)
            continue

        windows = file_history.get(row["file_id"], [])

        predicted_rate = predict_read_rate(
            model, windows, evaluation_time
        )

        if predicted_rate is not None:

            candidate["predicted_read_rate"] = predicted_rate

            candidate["migration_score"] = (
                calculate_migration_score(predicted_rate, windows)
            )

        result.append(candidate)

    return result


def train_hybrid_predictor(file_history, evaluation_time):
    """Select the best prediction strategy using historical validation."""

    # split historical data to prevent data leakage
    training_history, validation_history = split_file_history(
        file_history, evaluation_time
    )

    X_train, y_train = build_training_samples(training_history)
    X_val, y_val = build_training_samples(validation_history)

    # fallback if validation data is insufficient
    if len(X_val) < MIN_VALIDATION_SAMPLES:
        return "latest", None

    latest_predictions = []
    average_predictions = []

    # generate baseline predictions on the same validation samples
    for features in X_val:

        # feature 0: mean read rate
        average_predictions.append(features[0])

        # feature 1: latest read rate
        latest_predictions.append(features[1])

    # calculate validation errors for both baselines
    latest_error = mean_absolute_error(
        y_val, latest_predictions
    )

    average_error = mean_absolute_error(
        y_val, average_predictions
    )

    # select the better baseline first
    best_strategy = "latest"
    best_error = latest_error

    if average_error < best_error:
        best_strategy = "average"
        best_error = average_error

    # use the best baseline if ML training data is insufficient
    if len(X_train) < MIN_TRAINING_SAMPLES:
        return best_strategy, None

    # train the Ridge regression model
    model = make_pipeline(
        StandardScaler(),
        Ridge(alpha=RIDGE_ALPHA)
    )

    model.fit(X_train, y_train)

    # evaluate ML on the same validation dataset
    predictions = model.predict(X_val)

    ml_predictions = []

    for prediction in predictions:

        # read rates cannot be negative
        ml_predictions.append(max(0.0, float(prediction)))

    ml_error = mean_absolute_error(
        y_val, ml_predictions
    )

    # only use ML if it outperforms both baselines
    if ml_error < best_error:

        best_strategy = "ml"

        # retrain using all available historical data
        X_all, y_all = build_training_samples(file_history)

        model.fit(X_all, y_all)

        return best_strategy, model

    # ML provides no additional improvement
    return best_strategy, None


def predict_hybrid_read_rate(strategy, model, windows,
                             observed_rate, evaluation_time):
    """Return the estimated read rate and the actual prediction strategy."""

    # use the latest observed rate
    if strategy == "latest":
        return observed_rate, "latest"

    # fallback if historical data is insufficient
    if len(windows) < FEATURE_WINDOWS:
        return observed_rate, "latest"

    recent_windows = windows[-FEATURE_WINDOWS:]

    # check whether historical data is still fresh
    age = (evaluation_time - recent_windows[-1]["end"]).total_seconds()

    if age < 0 or age > WINDOW_SECONDS + SAMPLING_TOLERANCE_SECONDS:
        return observed_rate, "latest"

    # reject incomplete time series
    if not is_contiguous(recent_windows):
        return observed_rate, "latest"

    # use moving average
    if strategy == "average":
        read_rates = []

        for window in recent_windows:
            read_rates.append(window["read_rate"])

        return mean(read_rates), "average"

    # use ML prediction
    if strategy == "ml":
        prediction = predict_read_rate(model, windows, evaluation_time)

        if prediction is not None:
            return prediction, "ml"

    return observed_rate, "latest"


def apply_hybrid_predictions(candidates, file_history, evaluation_time):
    """Apply adaptive predictions and spatial locality scores."""

    if not candidates:
        return [], "latest"

    # select one prediction strategy for the current host
    strategy, model = train_hybrid_predictor(file_history, evaluation_time)
    result = []

    for row in candidates:
        candidate = row.copy()
        candidate["predicted_read_rate"] = None
        candidate["estimated_read_rate"] = row["read_rate"]
        candidate["prediction_strategy"] = "latest"
        candidate["spatial_factor"] = 1.0
        candidate["migration_score"] = row["read_rate"]

        # preserve original behaviour for mock data
        if row["is_mock"]:
            result.append(candidate)
            continue

        windows = file_history.get(row["file_id"], [])

        # record the actual strategy, including per-file fallback
        estimated_rate, actual_strategy = predict_hybrid_read_rate(
            strategy, model, windows, row["read_rate"], evaluation_time
        )

        # Fresh spatial data can still be useful when prediction falls back.
        spatial_factor = calculate_spatial_factor(windows, evaluation_time)
        candidate["estimated_read_rate"] = estimated_rate
        candidate["prediction_strategy"] = actual_strategy
        candidate["spatial_factor"] = spatial_factor
        candidate["migration_score"] = estimated_rate * spatial_factor

        if actual_strategy == "ml":
            candidate["predicted_read_rate"] = estimated_rate

        result.append(candidate)

    return result, strategy


def apply_predictions(candidates, activity, host_id, evaluation_time):
    """Apply adaptive predictive migration scoring using the existing interface."""

    if not candidates:
        return candidates

    file_history = prepare_file_history(activity, host_id, evaluation_time)
    result, _ = apply_hybrid_predictions(candidates, file_history, evaluation_time)

    return result
