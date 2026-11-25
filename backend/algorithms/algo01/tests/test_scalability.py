# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only

"""Measure ALGO-01 scalability without enforcing performance thresholds."""

import gc
import os
import tracemalloc
from random import Random
from statistics import mean
from time import perf_counter

import pytest

from backend.algorithms.algo01.inputs import D2Inputs, DEFAULTS
from backend.algorithms.algo01.candidates import collect_candidates
from backend.algorithms.algo01.prediction import (
    MAX_HISTORY_WINDOWS,
    prepare_file_history,
    predict_hybrid_read_rate,
    calculate_migration_score,
    apply_hybrid_predictions,
)
from backend.algorithms.algo01.strategy_controller import select_files
from backend.algorithms.algo01.tests.test_prediction import (
    HOST_ID, NOW, make_activity, generate_random_workload,
)


FILE_COUNTS = [15, 50, 100, 500, 1000, 5000]
BENCHMARK_ROUNDS = 3
BASE_SEED = 20000
SSD_CAPACITY = 1536 * 1024 ** 2
MAX_RECOMMENDATIONS = 5
MIB = 1024 ** 2

ALGORITHMS = ["D3", "MA + Spatial", "Adaptive Hybrid + Spatial"]


def generate_scalability_workload(file_count, seed):
    """Generate the same workload patterns as the placement benchmark."""

    rng = Random(seed)

    workload_types = [
        "stable", "increasing", "decreasing", "periodic", "random"
    ]

    activity = []

    for i in range(file_count):

        # keep the same workload proportions at every scale
        workload_type = workload_types[i % len(workload_types)]
        file_id = f"{workload_type}_{i}"
        file_size = rng.randint(64, 512) * MIB

        gap_type = rng.choice(["sequential", "random", "unknown"])

        if gap_type == "sequential":
            gap = 0
        elif gap_type == "random":
            gap = rng.randint(1, 1024) * 1024
        else:
            gap = None

        # only generate historical observations; no oracle is needed
        read_counts = generate_random_workload(
            rng, workload_type, minutes=MAX_HISTORY_WINDOWS
        )

        file_activity = make_activity(read_counts, gap=gap)

        for row in file_activity:
            row["file_id"] = file_id
            row["path"] = f"/pool/{file_id}.bin"
            row["file_size_bytes"] = file_size
            activity.append(row)

    rng.shuffle(activity)

    return activity


def apply_average_spatial(candidates, file_history):
    """Use moving average and the same spatial scoring as Hybrid."""

    result = []

    for row in candidates:
        candidate = row.copy()
        candidate["migration_score"] = row["read_rate"]

        if not row["is_mock"]:
            windows = file_history.get(row["file_id"], [])

            # reuse the production moving-average and fallback logic
            rate, _ = predict_hybrid_read_rate(
                "average", None, windows, row["read_rate"], NOW
            )

            candidate["migration_score"] = calculate_migration_score(
                rate, windows
            )

        result.append(candidate)

    return result


def run_scalability_case(activity, algorithm):
    """Measure candidate filtering, history preparation, scoring and selection."""

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

    # use identical input and eligibility rules for all strategies
    start = perf_counter()
    candidates = collect_candidates(context, devices, set())
    filter_end = perf_counter()

    history_time = 0.0
    scoring_time = 0.0
    strategy = "latest"
    strategy_counts = {"latest": 0, "average": 0, "ml": 0}
    scored_candidates = candidates

    if algorithm != "D3":

        # normalize up to 60 minutes of history
        history_start = perf_counter()
        file_history = prepare_file_history(activity, HOST_ID, NOW)
        history_time = perf_counter() - history_start

        scoring_start = perf_counter()

        if algorithm == "MA + Spatial":
            scored_candidates = apply_average_spatial(
                candidates, file_history
            )
            strategy = "average"

        elif algorithm == "Adaptive Hybrid + Spatial":
            # this is the same production path used by apply_predictions()
            scored_candidates, strategy = apply_hybrid_predictions(
                candidates, file_history, NOW
            )

        else:
            raise ValueError(f"unknown algorithm: {algorithm}")

        scoring_time = perf_counter() - scoring_start

    # use the real DP controller and record greedy fallback
    warnings = set()
    selection_start = perf_counter()

    selected = select_files(
        scored_candidates, SSD_CAPACITY, MAX_RECOMMENDATIONS, warnings
    )

    selection_end = perf_counter()

    # count actual per-file prediction strategies outside the timed stages
    if algorithm == "Adaptive Hybrid + Spatial":
        for row in scored_candidates:
            strategy_counts[row["prediction_strategy"]] += 1

    # only check structural correctness, not performance or accuracy
    used_space = sum(row["size"] for row in selected)
    selected_ids = {row["file_id"] for row in selected}
    assert used_space <= SSD_CAPACITY
    assert len(selected) <= MAX_RECOMMENDATIONS
    assert len(selected_ids) == len(selected)

    return {
        "eligible": len(candidates),
        "filter_time": filter_end - start,
        "history_time": history_time,
        "scoring_time": scoring_time,
        "selection_time": selection_end - selection_start,
        "total_time": selection_end - start,
        "fallback": "knapsack_budget_exceeded" in warnings,
        "selected": len(selected),
        "strategy": strategy,
        "strategy_counts": strategy_counts,
    }


def measure_peak_memory(activity, algorithm):
    """Measure additional traced Python memory in a separate execution."""

    # input records already exist; exclude workload generation from memory
    gc.collect()
    tracemalloc.start()

    try:
        baseline, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        run_scalability_case(activity, algorithm)
        _, peak = tracemalloc.get_traced_memory()
        return max(0, peak - baseline) / MIB

    finally:
        tracemalloc.stop()


@pytest.mark.benchmark
def test_scalability_benchmark():
    """Report scalability across increasing file counts."""

    # optional overrides for quick runs without editing the benchmark
    file_counts = [int(value) for value in os.getenv(
        "WSD_SCALE_FILES", ",".join(str(n) for n in FILE_COUNTS)
    ).split(",")]
    rounds = int(os.getenv("WSD_SCALE_ROUNDS", str(BENCHMARK_ROUNDS)))
    measure_memory = os.getenv("WSD_SCALE_MEMORY", "1") != "0"

    if rounds < 1 or not file_counts or min(file_counts) < 1:
        raise ValueError("file counts and benchmark rounds must be positive")

    results = []

    # warm up all code paths outside the reported measurements
    warmup_activity = generate_scalability_workload(15, BASE_SEED - 1)
    for algorithm in ALGORITHMS:
        run_scalability_case(warmup_activity, algorithm)
    del warmup_activity

    for file_count in file_counts:

        samples = {name: [] for name in ALGORITHMS}
        peaks = {name: None for name in ALGORITHMS}

        for repeat in range(rounds):
            seed = BASE_SEED + repeat
            activity = generate_scalability_workload(file_count, seed)

            # rotate execution order to reduce systematic order effects
            order = ALGORITHMS[repeat % len(ALGORITHMS):]
            order += ALGORITHMS[:repeat % len(ALGORITHMS)]

            for algorithm in order:
                gc.collect()
                result = run_scalability_case(activity, algorithm)
                samples[algorithm].append(result)

            # measure memory separately so tracing does not inflate timings
            # use the first seed only, for all algorithms at this scale
            if repeat == 0 and measure_memory:
                for algorithm in ALGORITHMS:
                    peaks[algorithm] = measure_peak_memory(activity, algorithm)

            del activity

        for algorithm in ALGORITHMS:
            rows = samples[algorithm]

            result = {
                "files": file_count,
                "records": file_count * MAX_HISTORY_WINDOWS,
                "algorithm": algorithm,
                "eligible": mean(row["eligible"] for row in rows),
                "filter_ms": mean(row["filter_time"] for row in rows) * 1000,
                "history_ms": mean(row["history_time"] for row in rows) * 1000,
                "scoring_ms": mean(row["scoring_time"] for row in rows) * 1000,
                "selection_ms": mean(row["selection_time"] for row in rows) * 1000,
                "total_ms": mean(row["total_time"] for row in rows) * 1000,
                "peak_mib": peaks[algorithm],
                "fallbacks": sum(row["fallback"] for row in rows),
                "selected": mean(row["selected"] for row in rows),
                "strategies": [row["strategy"] for row in rows],
                "ml_files": sum(row["strategy_counts"]["ml"] for row in rows),
                "average_files": sum(row["strategy_counts"]["average"] for row in rows),
                "latest_files": sum(row["strategy_counts"]["latest"] for row in rows),
            }

            results.append(result)

    lines = []
    lines.append("\n========== SCALABILITY BENCHMARK ==========")
    lines.append(f"Rounds per scale:     {rounds}")
    lines.append(f"History per file:     {MAX_HISTORY_WINDOWS} minutes")
    lines.append(f"SSD capacity:         {SSD_CAPACITY / MIB:.0f} MiB")
    lines.append(f"Max recommendations:  {MAX_RECOMMENDATIONS}")
    lines.append("Timing: mean of untraced runs; milliseconds.")
    lines.append("Memory: additional traced Python allocations, first seed only;")
    lines.append("        excludes input generation and may omit native allocations.")
    lines.append("DP time includes greedy fallback when the budget is exceeded.")
    lines.append("")

    header = (
        f"{'Files':>7} {'Records':>9} {'Algorithm':<26}"
        f"{'Eligible':>9} {'Filter':>10} {'History':>10}"
        f"{'Score':>10} {'Select':>10} {'Total':>10}"
        f"{'Peak MiB':>11} {'Fallback':>10}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for row in results:
        peak = "N/A" if row["peak_mib"] is None else f"{row['peak_mib']:.2f}"
        fallback = f"{row['fallbacks']}/{rounds}"

        lines.append(
            f"{row['files']:>7} {row['records']:>9} {row['algorithm']:<26}"
            f"{row['eligible']:>9.1f} {row['filter_ms']:>10.2f}"
            f"{row['history_ms']:>10.2f} {row['scoring_ms']:>10.2f}"
            f"{row['selection_ms']:>10.2f} {row['total_ms']:>10.2f}"
            f"{peak:>11} {fallback:>10}"
        )

    lines.append("\n========== HYBRID OVERHEAD ==========")
    lines.append(f"{'Files':>7} {'Hybrid / D3':>15} {'Hybrid / MA':>15}")

    for file_count in file_counts:
        group = {row["algorithm"]: row for row in results
                 if row["files"] == file_count}
        hybrid_time = group["Adaptive Hybrid + Spatial"]["total_ms"]
        d3_time = group["D3"]["total_ms"]
        ma_time = group["MA + Spatial"]["total_ms"]

        lines.append(
            f"{file_count:>7} {hybrid_time / d3_time:>14.2f}x"
            f" {hybrid_time / ma_time:>14.2f}x"
        )

    lines.append("\n========== HYBRID STRATEGY SELECTION ==========")
    lines.append(
        f"{'Files':>7} {'Latest runs':>12} {'MA runs':>12} {'ML runs':>12}"
        f" {'Latest files':>13} {'MA files':>12} {'ML files':>12}"
    )

    for row in results:
        if row["algorithm"] != "Adaptive Hybrid + Spatial":
            continue

        strategies = row["strategies"]
        lines.append(
            f"{row['files']:>7} {strategies.count('latest'):>12}"
            f" {strategies.count('average'):>12} {strategies.count('ml'):>12}"
            f" {row['latest_files']:>13} {row['average_files']:>12}"
            f" {row['ml_files']:>12}"
        )

    lines.append("=" * len(header))

    # report all results together, without performance assertions
    print("\n".join(lines))
