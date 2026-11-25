# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only

from datetime import datetime, timedelta, timezone
from random import Random
from statistics import mean
from time import perf_counter
from itertools import combinations
from fractions import Fraction

import pytest

from backend.algorithms.algo01.inputs import D2Inputs, DEFAULTS
from backend.algorithms.algo01.candidates import collect_candidates
from backend.algorithms.algo01.strategy_controller import select_files
from backend.algorithms.algo01 import prediction as prediction_module
from backend.algorithms.algo01.prediction import (
    prepare_file_history,
    extract_features,
    build_training_samples,
    train_model,
    predict_read_rate,
    calculate_migration_score,
    apply_predictions_legacy,
    apply_predictions as apply_production_predictions,
    train_hybrid_predictor,
    predict_hybrid_read_rate,
    apply_hybrid_predictions,
)


HOST_ID = "test_host"
FILE_ID = "test_file"

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def make_activity(read_counts, gap=None):
    """Generate historical FileActivity for testing."""

    activity = []

    start = NOW - timedelta(minutes=len(read_counts))

    # generate one FileActivity record for each minute
    for read_ops in read_counts:
        end = start + timedelta(seconds=60)

        activity.append({
            "host_id": HOST_ID,
            "file_id": FILE_ID,
            "device_id": "hdd0",
            "path": "/pool/test.bin",
            "window_start_utc": start.isoformat(),
            "window_end_utc": end.isoformat(),
            "read_ops": read_ops,
            "write_ops": 0,
            "read_bytes": read_ops * 4096,
            "write_bytes": 0,
            "file_size_bytes": 1024 * 1024,
            "read_average_gap": gap,
            "write_average_gap": None,
            "source": "linux_ebpf"
        })

        start = end

    return activity

def test_history_sorting_and_deduplication():
    activity = make_activity([60, 120, 180])

    # duplicate a record and reverse the order
    activity.append(activity[0].copy())
    activity.reverse()

    history = prepare_file_history(activity, HOST_ID, NOW)

    windows = history[FILE_ID]

    assert len(windows) == 3

    assert windows[0]["read_rate"] == 1.0
    assert windows[1]["read_rate"] == 2.0
    assert windows[2]["read_rate"] == 3.0


def test_overlapping_windows():
    activity = make_activity([60, 120, 180])

    # create a window overlapping the first two samples
    activity[0]["window_end_utc"] = (
        NOW - timedelta(seconds=90)
    ).isoformat()

    activity[0]["window_start_utc"] = (
        NOW - timedelta(seconds=150)
    ).isoformat()

    history = prepare_file_history(activity, HOST_ID, NOW)

    assert len(history[FILE_ID]) == 1
    assert history[FILE_ID][0]["read_rate"] == 3.0


def test_missing_window():
    activity = make_activity([60] * 15)

    # remove one sample from the middle
    activity.pop(7)

    history = prepare_file_history(activity, HOST_ID, NOW)

    X_train, y_train = build_training_samples(history)

    assert len(X_train) == 0
    assert len(y_train) == 0

def test_missing_spatial_features():
    activity = make_activity([60] * 5)

    history = prepare_file_history(activity, HOST_ID, NOW)

    features = extract_features(history[FILE_ID])

    assert len(features) == 10

    # no spatial locality information available
    assert features[6] == 0.0
    assert features[7] == 0.0
    assert features[8] == 0.0
    assert features[9] == 0.0


def test_sequential_read_features():
    activity = make_activity([60] * 5, gap=0)

    history = prepare_file_history(activity, HOST_ID, NOW)

    features = extract_features(history[FILE_ID])

    # zero gap is valid spatial locality information
    assert features[6] == 0.0
    assert features[8] == 1.0

def test_insufficient_training_data():
    activity = make_activity([60] * 10)

    history = prepare_file_history(activity, HOST_ID, NOW)

    model = train_model(history, NOW)

    assert model is None


def test_fallback_when_ml_has_no_improvement():
    # perfectly stable workload
    activity = make_activity([180] * 60)

    history = prepare_file_history(activity, HOST_ID, NOW)

    model = train_model(history, NOW)

    # D3 already predicts the workload perfectly
    assert model is None

def test_learning_periodic_workload():
    # burst of 1200 reads every 10 minutes
    read_counts = []

    for i in range(60):
        if (i + 1) % 10 == 0:
            read_counts.append(1200)
        else:
            read_counts.append(0)

    activity = make_activity(read_counts)

    history = prepare_file_history(activity, HOST_ID, NOW)

    model = train_model(history, NOW)

    assert model is not None

    prediction = predict_read_rate(
        model, history[FILE_ID], NOW
    )

    # actual average future read rate is 2 reads/s
    assert prediction == pytest.approx(2.0, abs=0.1)

    # ML prediction should outperform D3
    d3_prediction = history[FILE_ID][-1]["read_rate"]

    assert abs(prediction - 2.0) < abs(d3_prediction - 2.0)

def test_spatial_migration_score():
    sequential = make_activity([1200] * 5, gap=0)

    non_sequential = make_activity(
        [1200] * 5, gap=65536
    )

    unknown = make_activity([1200] * 5)

    seq_history = prepare_file_history(
        sequential, HOST_ID, NOW
    )

    random_history = prepare_file_history(
        non_sequential, HOST_ID, NOW
    )

    unknown_history = prepare_file_history(
        unknown, HOST_ID, NOW
    )

    # assume the same predicted read rate
    predicted_rate = 20.0

    seq_score = calculate_migration_score(
        predicted_rate, seq_history[FILE_ID]
    )

    random_score = calculate_migration_score(
        predicted_rate, random_history[FILE_ID]
    )

    unknown_score = calculate_migration_score(
        predicted_rate, unknown_history[FILE_ID]
    )

    assert seq_score == pytest.approx(20.0)
    assert random_score == pytest.approx(30.0)
    assert unknown_score == pytest.approx(20.0)

    assert random_score > seq_score



#####################################################################

##########################TIME FOR REAL TESTS########################

##### SCORE COMAPRE

def generate_random_workload(rng, workload_type, minutes=70):
    """Generate a synthetic workload with randomized parameters."""

    base_rate = rng.randint(5, 50)
    trend = rng.uniform(0.1, 0.8)

    burst_rate = rng.randint(20, 100)
    burst_period = rng.randint(3, 15)
    burst_phase = rng.randrange(burst_period)

    read_counts = []

    for minute in range(minutes):

        read_rate = base_rate

        # gradually increasing workload
        if workload_type == "increasing":
            read_rate += trend * minute

        # gradually decreasing workload
        elif workload_type == "decreasing":
            read_rate -= trend * minute

        # periodic bursts with randomized period and phase
        elif workload_type == "periodic":
            if minute % burst_period == burst_phase:
                read_rate += burst_rate

        # unpredictable workload
        elif workload_type == "random":
            read_rate = rng.uniform(0, base_rate * 2)

        # introduce random noise into the workload
        read_rate += rng.uniform(-3, 3)

        # read counts must be non-negative integers
        read_ops = max(0, round(read_rate * 60))

        read_counts.append(read_ops)

    return read_counts

def oracle_read_rate(future_counts):
    """Calculate the exact future read rate, oracle from ME!"""

    total_reads = sum(future_counts)
    duration = len(future_counts) * 60

    return total_reads / duration



######## DECIDSION COMPARE

def oracle_migration_score(future_counts, gap):
    """Calculate the exact future migration score."""

    # calculate the actual future read rate
    total_reads = sum(future_counts)
    duration = len(future_counts) * 60

    actual_rate = Fraction(total_reads, duration)

    # calculate the spatial locality factor independently
    spatial_factor = Fraction(1)

    if gap is not None:
        spatial_factor += Fraction(
            gap, gap + 64 * 1024
        )

    return actual_rate * spatial_factor


def oracle_select_files(candidates, capacity,
                        max_recommendations, oracle_scores):
    """Find the exact optimal placement by exhaustive search."""

    best_selection = []
    best_score = Fraction(0)
    best_space = 0

    max_count = min(max_recommendations, len(candidates))

    # enumerate all possible file combinations
    for count in range(1, max_count + 1):

        for combo in combinations(candidates, count):

            used_space = sum(row["size"] for row in combo)

            # skip combinations exceeding SSD capacity
            if used_space > capacity:
                continue

            total_score = Fraction(0)

            # evaluate using actual future workload
            for row in combo:
                total_score += oracle_scores[row["file_id"]]

            # update the optimal solution
            if total_score > best_score:

                best_selection = list(combo)
                best_score = total_score
                best_space = used_space

            # prefer smaller space if scores are equal
            elif total_score == best_score:

                if used_space < best_space:
                    best_selection = list(combo)
                    best_space = used_space

                elif used_space == best_space:

                    if count < len(best_selection):
                        best_selection = list(combo)

    return best_selection, best_score


def generate_placement_workload(seed):
    """Generate randomized file placement workloads."""

    rng = Random(seed)

    workload_types = [
        "stable",
        "increasing",
        "decreasing",
        "periodic",
        "random"
    ]

    activity = []
    oracle_scores = {}
    moving_average_rates = {}

    # generate 3 files for each workload type
    for workload_type in workload_types:

        for i in range(3):

            file_id = f"{workload_type}_{i}"

            # randomly generate file size
            file_size = rng.randint(64, 512) * 1024 ** 2

            # generate different spatial locality patterns
            gap_type = rng.choice([
                "sequential",
                "random",
                "unknown"
            ])

            if gap_type == "sequential":
                gap = 0

            elif gap_type == "random":
                gap = rng.randint(1, 1024) * 1024

            else:
                gap = None

            # generate 60 mins of history and 10 mins of future data
            read_counts = generate_random_workload(
                rng, workload_type
            )

            historical_counts = read_counts[:60]
            future_counts = read_counts[60:]

            # calculate the exact future migration benefit
            oracle_scores[file_id] = oracle_migration_score(
                future_counts, gap
            )

            # calculate the moving average baseline
            moving_average_rates[file_id] = (
                sum(historical_counts[-5:]) / 300
            )

            # only expose historical data to the production algorithm
            file_activity = make_activity(
                historical_counts, gap=gap
            )

            for row in file_activity:

                row["file_id"] = file_id
                row["path"] = f"/pool/{file_id}.bin"
                row["file_size_bytes"] = file_size

                activity.append(row)

    # randomize the order of historical records
    rng.shuffle(activity)

    # generate available SSD capacity between 512 MiB and 2 GiB
    capacity = rng.randint(512, 2048) * 1024 ** 2

    return activity, oracle_scores, moving_average_rates, capacity


def evaluate_placement(selected, oracle_scores):
    """Evaluate selected files using the actual future workload."""

    total_score = Fraction(0)
    used_space = 0

    for row in selected:

        file_id = row["file_id"]

        total_score += oracle_scores[file_id]
        used_space += row["size"]

    return total_score, used_space

def optimality_ratio(score, optimal_score):
    """Calculate how close a solution is to the optimum."""

    if optimal_score == 0:
        return None

    return float(score / optimal_score) * 100


@pytest.mark.benchmark
@pytest.mark.parametrize("seed", [1, 7, 42, 301, 2026])
def test_prediction_benchmark(seed):
    rng = Random(seed)

    workload_types = [
        "stable",
        "increasing",
        "decreasing",
        "periodic",
        "random"
    ]

    activity = []
    oracle_results = {}

    # generate 10 files for each workload type
    for workload_type in workload_types:

        for i in range(10):
            file_id = f"{workload_type}_{i}"

            read_counts = generate_random_workload(
                rng, workload_type
            )

            # separate historical and future workload
            historical_counts = read_counts[:60]
            future_counts = read_counts[60:]

            # calculate the exact answer using future data
            oracle_results[file_id] = oracle_read_rate(
                future_counts
            )

            # only historical data is passed to ALGO-01
            file_activity = make_activity(historical_counts)

            for row in file_activity:
                row["file_id"] = file_id
                row["path"] = f"/pool/{file_id}.bin"

                activity.append(row)

    # randomize incoming FileActivity
    rng.shuffle(activity)

    history = prepare_file_history(
        activity, HOST_ID, NOW
    )

    # measure model training overhead
    start_time = perf_counter()

    model = train_model(history, NOW)

    training_time = perf_counter() - start_time

    d3_errors = []
    d4_errors = []
    average_errors = []

    fallback_count = 0

    # compare predictions against the oracle
    for file_id, correct_rate in oracle_results.items():

        windows = history[file_id]

        # D3 prediction
        d3_prediction = windows[-1]["read_rate"]

        # simple historical average as another baseline
        historical_rates = []

        for window in windows[-5:]:
            historical_rates.append(window["read_rate"])

        average_prediction = mean(historical_rates)

        # D4 prediction
        d4_prediction = predict_read_rate(
            model, windows, NOW
        )

        # apply the actual D4 fallback behaviour
        if d4_prediction is None:
            d4_prediction = d3_prediction
            fallback_count += 1

        # calculate absolute prediction errors
        d3_errors.append(abs(d3_prediction - correct_rate))
        d4_errors.append(abs(d4_prediction - correct_rate))
        average_errors.append(
            abs(average_prediction - correct_rate)
        )

    d3_mae = mean(d3_errors)
    d4_mae = mean(d4_errors)
    average_mae = mean(average_errors)

    improvement = 0.0

    if d3_mae > 0:
        improvement = (
            (d3_mae - d4_mae) / d3_mae
        ) * 100

    # report benchmark results without enforcing accuracy
    print(f"\n=== Benchmark Seed {seed} ===")
    print(f"Files: {len(oracle_results)}")
    print(f"D3 MAE: {d3_mae:.4f}")
    print(f"Moving Average MAE: {average_mae:.4f}")
    print(f"D4 MAE: {d4_mae:.4f}")
    print(f"Improvement: {improvement:.2f}%")
    print(f"Training time: {training_time:.4f}s")
    print(f"Fallback count: {fallback_count}")


def run_file_placement_benchmark(seed):

    activity, oracle_scores, moving_average_rates, capacity = (
        generate_placement_workload(seed)
    )

    max_recommendations = 5

    # use the existing candidate filtering policy
    context = D2Inputs(
        now=NOW,
        timestamp=NOW.isoformat(),
        host=HOST_ID,
        config=DEFAULTS.copy(),
        activity=activity
    )

    devices = {
        "hdd0": {
            "is_available": True,
            "media_type": "hdd"
        }
    }

    candidates = collect_candidates(
        context, devices, set()
    )

    # calculate the exact optimal placement first
    oracle_selected, optimal_score = oracle_select_files(
        candidates,
        capacity,
        max_recommendations,
        oracle_scores
    )

    # D3: observed read rate + Knapsack
    d3_warnings = set()

    start = perf_counter()

    d3_selected = select_files(
        candidates,
        capacity,
        max_recommendations,
        d3_warnings
    )

    d3_time = perf_counter() - start

    # Moving Average + Knapsack
    average_candidates = []

    start = perf_counter()

    for row in candidates:

        candidate = row.copy()

        candidate["migration_score"] = (
            moving_average_rates[row["file_id"]]
        )

        average_candidates.append(candidate)

    average_warnings = set()

    average_selected = select_files(
        average_candidates,
        capacity,
        max_recommendations,
        average_warnings
    )

    average_time = perf_counter() - start

    # D4: ML prediction + spatial locality + Knapsack
    d4_warnings = set()

    start = perf_counter()

    d4_candidates = apply_predictions_legacy(
        candidates, activity, HOST_ID, NOW
    )

    d4_selected = select_files(
        d4_candidates,
        capacity,
        max_recommendations,
        d4_warnings
    )

    d4_time = perf_counter() - start

    # evaluate all selected files using the same oracle
    d3_score, d3_space = evaluate_placement(
        d3_selected, oracle_scores
    )

    average_score, average_space = evaluate_placement(
        average_selected, oracle_scores
    )

    d4_score, d4_space = evaluate_placement(
        d4_selected, oracle_scores
    )

    # calculate the optimality ratio
    d3_ratio = optimality_ratio(d3_score, optimal_score)

    average_ratio = optimality_ratio(
        average_score, optimal_score
    )

    d4_ratio = optimality_ratio(d4_score, optimal_score)

    # calculate improvement over D3
    improvement = None

    if d3_score > 0:
        improvement = float(
            (d4_score - d3_score) / d3_score
        ) * 100

    # count candidates using the ML prediction
    ml_count = 0

    for row in d4_candidates:

        if row.get("predicted_read_rate") is not None:
            ml_count += 1

    # return benchmark results for aggregate analysis
    return {
        "seed": seed,
        "generated_files": len(oracle_scores),
        "eligible_candidates": len(candidates),
        "ml_count": ml_count,

        "oracle_score": optimal_score,

        "d3_score": d3_score,
        "average_score": average_score,
        "d4_score": d4_score,

        "d3_ratio": d3_ratio,
        "average_ratio": average_ratio,
        "d4_ratio": d4_ratio,

        "d3_time": d3_time,
        "average_time": average_time,
        "d4_time": d4_time,

        "improvement": improvement,

        "d3_space": d3_space,
        "average_space": average_space,
        "d4_space": d4_space,

        "d3_optimal": d3_score == optimal_score,
        "average_optimal": average_score == optimal_score,
        "d4_optimal": d4_score == optimal_score
    }


BENCHMARK_ROUNDS = 100


@pytest.mark.benchmark
def test_file_placement_benchmark():
    """Evaluate file placement across randomized workloads."""

    results = []

    # run all randomized experiments
    for seed in range(BENCHMARK_ROUNDS):

        result = run_file_placement_benchmark(seed)

        results.append(result)

    # calculate overall workload statistics
    total_files = sum(r["generated_files"] for r in results)
    total_candidates = sum(r["eligible_candidates"] for r in results)
    total_ml = sum(r["ml_count"] for r in results)

    # exclude workloads without positive oracle benefit
    valid_results = []

    for row in results:
        if row["oracle_score"] > 0:
            valid_results.append(row)

    lines = []

    lines.append("\n========== FILE PLACEMENT BENCHMARK ==========")
    lines.append(f"Experiments:          {len(results)}")
    lines.append(f"Valid experiments:    {len(valid_results)}")
    lines.append(f"Generated files:      {total_files}")
    lines.append(f"Eligible candidates:  {total_candidates}")
    lines.append(f"ML-enabled files:     {total_ml}")
    lines.append(f"ML fallback files:    {total_candidates - total_ml}")

    if not valid_results:
        lines.append("No workloads with positive oracle benefit.")
        print("\n".join(lines))
        return

    # compare all algorithms using the same metrics
    algorithms = [
        ("D3", "d3"),
        ("Moving Average", "average"),
        ("D4 ML + Spatial", "d4")
    ]

    lines.append("")
    lines.append(
        f"{'Algorithm':<20}"
        f"{'Avg Opt.':>12}"
        f"{'Min Opt.':>12}"
        f"{'Max Opt.':>12}"
        f"{'Optimal':>12}"
        f"{'Time(ms)':>12}"
    )

    lines.append("-" * 80)

    for name, key in algorithms:

        ratios = []
        times = []
        optimal_count = 0

        # collect metrics across all valid experiments
        for row in valid_results:

            ratios.append(row[f"{key}_ratio"])
            times.append(row[f"{key}_time"])

            if row[f"{key}_optimal"]:
                optimal_count += 1

        optimal_label = f"{optimal_count}/{len(valid_results)}"

        lines.append(
            f"{name:<20}"
            f"{mean(ratios):>11.2f}%"
            f"{min(ratios):>11.2f}%"
            f"{max(ratios):>11.2f}%"
            f"{optimal_label:>12}"
            f"{mean(times) * 1000:>12.3f}"
        )

    # compare D4 against the original D3 algorithm
    wins = 0
    ties = 0
    losses = 0

    improvements = []

    for row in valid_results:

        if row["d4_score"] > row["d3_score"]:
            wins += 1

        elif row["d4_score"] == row["d3_score"]:
            ties += 1

        else:
            losses += 1

        if row["improvement"] is not None:
            improvements.append(row["improvement"])

    lines.append("\n========== D4 VS D3 ==========")
    lines.append(f"Wins:                 {wins}")
    lines.append(f"Ties:                 {ties}")
    lines.append(f"Losses:               {losses}")
    lines.append(f"Win rate:             {wins / len(valid_results) * 100:.2f}%")

    if improvements:
        lines.append(
            f"Average improvement:  {mean(improvements):.2f}%"
        )

        lines.append(
            f"Best improvement:     {max(improvements):.2f}%"
        )

        lines.append(
            f"Worst improvement:    {min(improvements):.2f}%"
        )

    # calculate the average optimality gap
    d3_gap = 100 - mean(r["d3_ratio"] for r in valid_results)
    d4_gap = 100 - mean(r["d4_ratio"] for r in valid_results)

    lines.append(f"D3 optimality gap:    {d3_gap:.2f}%")
    lines.append(f"D4 optimality gap:    {d4_gap:.2f}%")

    if d3_gap > 0:
        gap_reduction = (d3_gap - d4_gap) / d3_gap * 100

        lines.append(
            f"Gap reduction:        {gap_reduction:.2f}%"
        )

    lines.append("=" * 80)

    # print the complete summary only once
    print("\n".join(lines))


######### Ablation Study

def build_ablation_candidates(candidates, predicted_candidates,
                              file_history, moving_average_rates):
    """Build candidates with different migration scoring strategies."""

    groups = {
        "D3": [],
        "D3 + Spatial": [],
        "Moving Average": [],
        "MA + Spatial": [],
        "ML Only": [],
        "ML + Spatial": [],
        "D4 Production": []
    }

    # index candidates processed by the production ML module
    prediction_map = {}

    for row in predicted_candidates:
        prediction_map[row["file_id"]] = row

    for row in candidates:

        file_id = row["file_id"]

        # collect different read rate estimates
        observed_rate = row["read_rate"]
        average_rate = moving_average_rates[file_id]

        predicted_row = prediction_map[file_id]
        predicted_rate = predicted_row.get("predicted_read_rate")

        # fallback to D3 if ML prediction is unavailable
        if predicted_rate is None:
            predicted_rate = observed_rate

        # calculate the spatial factor independently of ML
        windows = file_history.get(file_id, [])

        spatial_factor = calculate_migration_score(
            1.0, windows
        )

        # calculate scores for different scoring strategies
        scores = {
            "D3": observed_rate,
            "D3 + Spatial": observed_rate * spatial_factor,
            "Moving Average": average_rate,
            "MA + Spatial": average_rate * spatial_factor,
            "ML Only": predicted_rate,
            "ML + Spatial": predicted_rate * spatial_factor
        }

        # keep the same candidate properties for all groups
        for name, score in scores.items():

            candidate = row.copy()
            candidate["migration_score"] = score

            groups[name].append(candidate)

        # preserve the original D4 production behaviour
        groups["D4 Production"].append(predicted_row.copy())

    return groups

def run_ablation_benchmark(seed):
    """Evaluate different migration scoring strategies."""

    activity, oracle_scores, moving_average_rates, capacity = (
        generate_placement_workload(seed)
    )

    max_recommendations = 5

    # use the original candidate filtering policy
    context = D2Inputs(
        now=NOW,
        timestamp=NOW.isoformat(),
        host=HOST_ID,
        config=DEFAULTS.copy(),
        activity=activity
    )

    devices = {
        "hdd0": {
            "is_available": True,
            "media_type": "hdd"
        }
    }

    candidates = collect_candidates(
        context, devices, set()
    )

    # calculate the exact optimal placement
    oracle_selected, optimal_score = oracle_select_files(
        candidates,
        capacity,
        max_recommendations,
        oracle_scores
    )

    if optimal_score == 0:
        return None

    # generate predictions using the original D4 implementation
    predicted_candidates = apply_predictions_legacy(
        candidates, activity, HOST_ID, NOW
    )

    file_history = prepare_file_history(
        activity, HOST_ID, NOW
    )

    # construct the original experimental groups
    groups = build_ablation_candidates(
        candidates,
        predicted_candidates,
        file_history,
        moving_average_rates
    )

    # generate predictions using the adaptive hybrid strategy
    hybrid_candidates, hybrid_strategy = (
        apply_hybrid_predictions(
            candidates,
            file_history,
            NOW
        )
    )

    # add the new experimental group
    groups["Adaptive Hybrid + Spatial"] = hybrid_candidates

    result = {}

    # evaluate all scoring strategies using the same DP
    for name, group_candidates in groups.items():

        selected = select_files(
            group_candidates,
            capacity,
            max_recommendations,
            set()
        )

        # evaluate using the actual future workload
        score, used_space = evaluate_placement(
            selected, oracle_scores
        )

        result[name] = {
            "score": score,
            "ratio": optimality_ratio(score, optimal_score),
            "optimal": score == optimal_score,
            "used_space": used_space
        }

    # record the prediction strategy selected by Hybrid
    result["hybrid_strategy"] = hybrid_strategy

    return result

@pytest.mark.benchmark
def test_file_placement_ablation():
    """Measure component contributions; D4 Production denotes the legacy baseline."""

    results = []

    # run all randomized experiments
    for seed in range(100, 1100):

        result = run_ablation_benchmark(seed)

        if result is not None:
            results.append(result)

    if not results:
        print("No valid experiments.")
        return

    algorithms = [
        "D3",
        "D3 + Spatial",
        "Moving Average",
        "MA + Spatial",
        "ML Only",
        "ML + Spatial",
        "D4 Production",
        "Adaptive Hybrid + Spatial"
    ]

    average_ratios = {}
    lines = []

    lines.append("\n========== ABLATION STUDY ==========")
    lines.append(f"Valid experiments: {len(results)}")
    lines.append("")

    lines.append(
        f"{'Algorithm':<28}"
        f"{'Avg Opt.':>12}"
        f"{'Min Opt.':>12}"
        f"{'Optimal':>12}"
        f"{'Wins':>8}"
        f"{'Ties':>8}"
        f"{'Losses':>8}"
    )

    lines.append("-" * 82)

    for name in algorithms:

        ratios = []
        optimal_count = 0

        wins = 0
        ties = 0
        losses = 0

        for row in results:

            ratios.append(row[name]["ratio"])

            if row[name]["optimal"]:
                optimal_count += 1

            # compare each strategy against D3
            score = row[name]["score"]
            baseline_score = row["D3"]["score"]

            if score > baseline_score:
                wins += 1

            elif score == baseline_score:
                ties += 1

            else:
                losses += 1

        average_ratios[name] = mean(ratios)

        optimal_label = f"{optimal_count}/{len(results)}"

        lines.append(
            f"{name:<28}"
            f"{mean(ratios):>11.2f}%"
            f"{min(ratios):>11.2f}%"
            f"{optimal_label:>12}"
            f"{wins:>8}"
            f"{ties:>8}"
            f"{losses:>8}"
        )

    # measure the contribution of each component
    d3 = average_ratios["D3"]
    d3_spatial = average_ratios["D3 + Spatial"]

    ma = average_ratios["Moving Average"]
    ma_spatial = average_ratios["MA + Spatial"]

    ml = average_ratios["ML Only"]
    ml_spatial = average_ratios["ML + Spatial"]

    production = average_ratios["D4 Production"]

    lines.append("\n========== COMPONENT CONTRIBUTIONS ==========")

    # measure ML contribution with and without spatial locality
    lines.append(
        f"ML without Spatial:       {ml - d3:+.2f} pp"
    )

    lines.append(
        f"ML with Spatial:          {ml_spatial - d3_spatial:+.2f} pp"
    )

    # measure spatial contribution with different rate estimators
    lines.append(
        f"Spatial with D3:          {d3_spatial - d3:+.2f} pp"
    )

    lines.append(
        f"Spatial with MA:          {ma_spatial - ma:+.2f} pp"
    )

    lines.append(
        f"Spatial with ML:          {ml_spatial - ml:+.2f} pp"
    )

    # compare ML against moving average directly
    lines.append(
        f"ML vs MA:                 {ml - ma:+.2f} pp"
    )

    lines.append(
        f"ML vs MA with Spatial:    {ml_spatial - ma_spatial:+.2f} pp"
    )

    # measure interaction between ML and spatial locality
    interaction = (
        ml_spatial - ml - d3_spatial + d3
    )

    lines.append(
        f"ML-Spatial interaction:   {interaction:+.2f} pp"
    )

    # average marginal contribution of each component
    ml_contribution = (
        (ml - d3) +
        (ml_spatial - d3_spatial)
    ) / 2

    spatial_contribution = (
        (d3_spatial - d3) +
        (ml_spatial - ml)
    ) / 2

    lines.append("\n========== CONTRIBUTION BREAKDOWN ==========")

    lines.append(
        f"ML contribution:          {ml_contribution:+.2f} pp"
    )

    lines.append(
        f"Spatial contribution:     {spatial_contribution:+.2f} pp"
    )

    lines.append(
        f"Combined improvement:     {ml_spatial - d3:+.2f} pp"
    )

    lines.append(
        f"Production improvement:   {production - d3:+.2f} pp"
    )

    lines.append(
        f"Production fallback effect: {production - ml_spatial:+.2f} pp"
    )

    # evaluate adaptive hybrid performance
    hybrid = average_ratios["Adaptive Hybrid + Spatial"]

    strategy_counts = {
        "latest": 0,
        "average": 0,
        "ml": 0
    }

    hybrid_ma_wins = 0
    hybrid_ma_ties = 0
    hybrid_ma_losses = 0

    hybrid_d4_wins = 0
    hybrid_d4_ties = 0
    hybrid_d4_losses = 0

    # compare Hybrid against MA + Spatial and D4 Production
    for row in results:

        strategy = row["hybrid_strategy"]

        strategy_counts[strategy] += 1

        hybrid_score = row["Adaptive Hybrid + Spatial"]["score"]
        ma_score = row["MA + Spatial"]["score"]
        production_score = row["D4 Production"]["score"]

        # compare against moving average
        if hybrid_score > ma_score:
            hybrid_ma_wins += 1

        elif hybrid_score == ma_score:
            hybrid_ma_ties += 1

        else:
            hybrid_ma_losses += 1

        # compare against original D4
        if hybrid_score > production_score:
            hybrid_d4_wins += 1

        elif hybrid_score == production_score:
            hybrid_d4_ties += 1

        else:
            hybrid_d4_losses += 1

    lines.append("\n========== ADAPTIVE HYBRID EVALUATION ==========")

    lines.append(
        f"Hybrid avg optimality:      {hybrid:.2f}%"
    )

    lines.append(
        f"Hybrid vs D3:              {hybrid - d3:+.2f} pp"
    )

    lines.append(
        f"Hybrid vs MA + Spatial:    {hybrid - ma_spatial:+.2f} pp"
    )

    lines.append(
        f"Hybrid vs ML + Spatial:    {hybrid - ml_spatial:+.2f} pp"
    )

    lines.append(
        f"Hybrid vs D4 Production:   {hybrid - production:+.2f} pp"
    )

    # report strategy selection frequency
    lines.append("\n========== STRATEGY SELECTION ==========")

    for strategy, count in strategy_counts.items():

        percentage = count / len(results) * 100

        lines.append(
            f"{strategy:<20}: {count:>4}/{len(results)}"
            f" ({percentage:.2f}%)"
        )

    # report paired comparisons
    lines.append("\n========== HYBRID VS MA + SPATIAL ==========")

    lines.append(f"Wins:    {hybrid_ma_wins}")
    lines.append(f"Ties:    {hybrid_ma_ties}")
    lines.append(f"Losses:  {hybrid_ma_losses}")

    lines.append("\n========== HYBRID VS D4 PRODUCTION ==========")

    lines.append(f"Wins:    {hybrid_d4_wins}")
    lines.append(f"Ties:    {hybrid_d4_ties}")
    lines.append(f"Losses:  {hybrid_d4_losses}")

    lines.append("=" * 82)

    # print all experiment results at once
    print("\n".join(lines))


def test_production_hybrid_integration():
    activity, _, _, _ = generate_placement_workload(42)
    context = D2Inputs(
        now=NOW,
        timestamp=NOW.isoformat(),
        host=HOST_ID,
        config=DEFAULTS.copy(),
        activity=activity
    )
    devices = {"hdd0": {"is_available": True, "media_type": "hdd"}}
    candidates = collect_candidates(context, devices, set())
    original_candidates = [row.copy() for row in candidates]

    result = apply_production_predictions(candidates, activity, HOST_ID, NOW)
    expected, _ = apply_hybrid_predictions(
        candidates, prepare_file_history(activity, HOST_ID, NOW), NOW
    )

    assert candidates
    assert len(result) == len(candidates)
    assert result == expected
    assert candidates == original_candidates

    for original, updated in zip(candidates, result):
        for key, value in original.items():
            assert updated[key] == value

        assert updated["prediction_strategy"] in ("latest", "average", "ml")
        assert updated["estimated_read_rate"] >= 0
        assert 1.0 <= updated["spatial_factor"] <= 2.0
        assert updated["migration_score"] == pytest.approx(
            updated["estimated_read_rate"] * updated["spatial_factor"]
        )

        if updated["prediction_strategy"] == "ml":
            assert updated["predicted_read_rate"] == updated["estimated_read_rate"]
        else:
            assert updated["predicted_read_rate"] is None


def make_hybrid_test_candidate(is_mock=False):
    return {
        "file_id": FILE_ID,
        "source": "hdd0",
        "size": 1024 ** 2,
        "read_rate": 20.0,
        "is_mock": is_mock
    }


def test_production_hybrid_fallback():
    candidates = [make_hybrid_test_candidate()]
    candidate = apply_production_predictions(candidates, [], HOST_ID, NOW)[0]

    assert candidate["prediction_strategy"] == "latest"
    assert candidate["predicted_read_rate"] is None
    assert candidate["estimated_read_rate"] == 20.0
    assert candidate["spatial_factor"] == 1.0
    assert candidate["migration_score"] == 20.0


def test_production_hybrid_mock():
    candidates = [make_hybrid_test_candidate(is_mock=True)]
    activity = make_activity([1200] * 60, gap=1024 ** 2)
    candidate = apply_production_predictions(candidates, activity, HOST_ID, NOW)[0]

    assert candidate["prediction_strategy"] == "latest"
    assert candidate["predicted_read_rate"] is None
    assert candidate["estimated_read_rate"] == 20.0
    assert candidate["spatial_factor"] == 1.0
    assert candidate["migration_score"] == 20.0


def test_production_hybrid_fallback_preserves_spatial(monkeypatch):
    # force host-wide ML selection, but provide too little history for this file
    monkeypatch.setattr(prediction_module, "train_hybrid_predictor",
                        lambda history, now: ("ml", None))
    activity = make_activity([1200] * 2, gap=65536)
    candidates = [make_hybrid_test_candidate()]
    candidate = apply_production_predictions(candidates, activity, HOST_ID, NOW)[0]

    assert candidate["prediction_strategy"] == "latest"
    assert candidate["predicted_read_rate"] is None
    assert candidate["estimated_read_rate"] == 20.0
    assert candidate["spatial_factor"] == pytest.approx(1.5)
    assert candidate["migration_score"] == pytest.approx(30.0)


def test_production_hybrid_average(monkeypatch):
    monkeypatch.setattr(prediction_module, "train_hybrid_predictor",
                        lambda history, now: ("average", None))
    activity = make_activity([60, 120, 180, 240, 300], gap=65536)
    candidates = [make_hybrid_test_candidate()]
    candidate = apply_production_predictions(candidates, activity, HOST_ID, NOW)[0]

    assert candidate["prediction_strategy"] == "average"
    assert candidate["predicted_read_rate"] is None
    assert candidate["estimated_read_rate"] == pytest.approx(3.0)
    assert candidate["migration_score"] == pytest.approx(4.5)


def test_production_hybrid_ml(monkeypatch):
    class FixedModel:
        def predict(self, features):
            return [7.0]

    monkeypatch.setattr(prediction_module, "train_hybrid_predictor",
                        lambda history, now: ("ml", FixedModel()))
    activity = make_activity([1200] * 5, gap=65536)
    candidates = [make_hybrid_test_candidate()]
    candidate = apply_production_predictions(candidates, activity, HOST_ID, NOW)[0]

    assert candidate["prediction_strategy"] == "ml"
    assert candidate["predicted_read_rate"] == 7.0
    assert candidate["estimated_read_rate"] == 7.0
    assert candidate["migration_score"] == pytest.approx(10.5)
