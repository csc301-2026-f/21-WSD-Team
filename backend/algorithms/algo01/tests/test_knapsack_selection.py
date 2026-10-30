# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
# Knapsack unit tests
import random
import time
import pytest
import json
import backend.algorithms.algo01.knapsack_selection as knapsack_module
from pathlib import Path
from unittest.mock import patch
from itertools import combinations
from backend.algorithms.algo01 import evaluate_raid0_policy
from backend.algorithms.algo01.knapsack_selection import select_files_knapsack, KnapsackBudgetExceeded
from backend.algorithms.algo01.knapsack_selection import (StateKey, StateValue, prune_dominated_states)
from backend.algorithms.algo01.strategy_controller import select_files

gb = 1024 ** 3

# A case that Knapsack supposed to perform better than greedy
def test_knapsack_optimal_selection():
    candidates = [
        {"file_id": "A", "size": 6 * gb, "read_rate": 10},
        {"file_id": "B", "size": 5 * gb, "read_rate": 9},
        {"file_id": "C", "size": 5 * gb, "read_rate": 9},
    ]

    selected = select_files_knapsack(
        candidates,
        capacity=10 * gb,
        max_recommendations=2,
        warnings=set()
    )

    assert [row["file_id"] for row in selected] == ["B", "C"]

# A case that insufficient space
def test_insufficient_capacity():
    candidates = [
        {"file_id": "A", "size": 6 * gb, "read_rate": 10},
    ]

    selected = select_files_knapsack(
        candidates, 5 * gb, 2, set()
    )

    assert selected == []

# A case that can only allows one file to be recommended 
def test_max_recommendation():
    candidates = [
        {"file_id": "A", "size": 1 * gb, "read_rate": 10},
        {"file_id": "B", "size": 1 * gb, "read_rate": 9},
    ]

    selected = select_files_knapsack(
        candidates, 10 * gb, 1, set()
    )

    assert [row["file_id"] for row in selected] == ["A"]

# A case test tie breaker, choose used_space least
def test_tie_breaking_space():
    candidates = [
        {"file_id": "A", "size": 6 * gb, "read_rate": 10},
        {"file_id": "B", "size": 4 * gb, "read_rate": 10},
    ]

    selected = select_files_knapsack(
        candidates, 6 * gb, 2, set()
    )

    assert [row["file_id"] for row in selected] == ["B"]

# A case test tie breaker, used_space same, choose file_count least
def test_tie_breaking_count():
    candidates = [
        {"file_id": "A", "size": 4 * gb, "read_rate": 10},
        {"file_id": "B", "size": 2 * gb, "read_rate": 5},
        {"file_id": "C", "size": 2 * gb, "read_rate": 5},
    ]

    selected = select_files_knapsack(
        candidates, 4 * gb, 2, set()
    )

    assert [row["file_id"] for row in selected] == ["A"]

# A case to test prune
def test_dominance_pruning():
    states = {
        StateKey(3, 1): StateValue(10, (0,)),
        StateKey(5, 1): StateValue(8, (1,)),
        StateKey(4, 1): StateValue(12, (2,)),
        StateKey(7, 2): StateValue(22, (0, 2)),
    }

    pruned = prune_dominated_states(states)

    assert StateKey(3, 1) in pruned
    assert StateKey(4, 1) in pruned
    assert StateKey(5, 1) not in pruned
    assert StateKey(7, 2) in pruned

@pytest.mark.parametrize("seed", [1, 7, 42, 301, 2026])
@pytest.mark.parametrize("capacity", [gb // 2, gb, 2 * gb])
# A test designed for make sure prune doesn't prune out optimal solution
def test_knapsack_against_bruteforce(seed, capacity):
    candidates = generate_candidates(10, seed=seed)
    max_recommendations = 5
    # capacity = 1 * gb
    # max_recommendations = 5

    # Our Knapsack DP
    selected = select_files_knapsack(
        candidates, capacity, max_recommendations, set()
    )

    # Brute Force: enumerate all feasible combinations
    feasible = []

    for count in range(max_recommendations + 1):
        for combo in combinations(candidates, count):
            if sum(row["size"] for row in combo) <= capacity:
                feasible.append(combo)

    # Apply the same tie-breaking rules
    def score(rows):
        return (
            round(sum(row["read_rate"] for row in rows), 3),
            -sum(row["size"] for row in rows),
            -len(rows)
        )

    optimal = max(feasible, key=score)

    assert score(selected) == score(optimal)

# Generate random candidates for performance testing
def generate_candidates(count, seed=301):
    rng = random.Random(seed)
    candidates = []

    for i in range(count):
        candidates.append({
            "file_id": f"file-{i:04d}",
            "size": rng.randint(64, 512) * 1024 ** 2,
            "read_rate": round(rng.uniform(0.1, 20.0), 3)
        })

    return candidates

class PruningStats:
    """Track DP state counts before and after dominance pruning."""

    def __init__(self):
        self.peak_before = 0
        self.peak_after = 0
        self.total_pruned = 0
        self.original_prune = knapsack_module.prune_dominated_states

    def track(self, states):
        self.peak_before = max(self.peak_before, len(states))

        pruned = self.original_prune(states)

        self.peak_after = max(self.peak_after, len(pruned))
        self.total_pruned += len(states) - len(pruned)

        return pruned

def benchmark_knapsack():
    capacity = 1 * gb
    max_recommendations = 10

    for count in [10, 20, 50, 100]:
        candidates = generate_candidates(count)

        # Benchmark execution time without instrumentation
        start = time.perf_counter()
        selected = select_files_knapsack(
            candidates, capacity, max_recommendations, set()
        )
        elapsed = time.perf_counter() - start

        # Collect DP pruning statistics separately
        stats = PruningStats()

        with patch.object(knapsack_module, "prune_dominated_states", stats.track):
            measured_selected = select_files_knapsack(
                candidates, capacity, max_recommendations, set()
            )

        assert selected == measured_selected

        # Verify selection constraints
        used_space = sum(row["size"] for row in selected)
        total_read_rate = sum(row["read_rate"] for row in selected)

        assert used_space <= capacity
        assert len(selected) <= max_recommendations
        assert len({row["file_id"] for row in selected}) == len(selected)

        # Print benchmark results
        print(
            f"\nCandidates: {count}"
            f" | Time: {elapsed:.6f}s"
            f" | Selected: {len(selected)}"
            f" | Used: {used_space / gb:.2f} GiB"
            f" | Total Read Rate: {total_read_rate:.3f}"
        )

        print(
            f"Peak Before Pruning: {stats.peak_before}"
            f" | Peak After Pruning: {stats.peak_after}"
            f" | Total Pruned: {stats.total_pruned}"
        )

# Knapsack should stop when exceeding the DP state budget
def test_knapsack_budget_exceeded(monkeypatch):
    monkeypatch.setattr(knapsack_module, "MAX_DP_STATES", 1)

    candidates = [
        {"file_id": "A", "size": 1 * gb, "read_rate": 10},
        {"file_id": "B", "size": 1 * gb, "read_rate": 9},
    ]

    with pytest.raises(KnapsackBudgetExceeded):
        select_files_knapsack(
            candidates,
            capacity=2 * gb,
            max_recommendations=2,
            warnings=set()
        )

# A case with sufficient budget
def test_strategy_uses_knapsack():
    candidates = [
        {"file_id": "A", "size": 6 * gb, "read_rate": 10},
        {"file_id": "B", "size": 5 * gb, "read_rate": 9},
        {"file_id": "C", "size": 5 * gb, "read_rate": 9},
    ]

    selected = select_files(candidates, 10 * gb, 2, set())

    assert [row["file_id"] for row in selected] == ["B", "C"]

# A case with insufficient budget
def test_strategy_falls_back_to_greedy(monkeypatch):
    monkeypatch.setattr(knapsack_module, "MAX_DP_STATES", 1)

    candidates = [
        {"file_id": "A", "size": 6 * gb, "read_rate": 10},
        {"file_id": "B", "size": 5 * gb, "read_rate": 9},
        {"file_id": "C", "size": 5 * gb, "read_rate": 9},
    ]

    warnings = set()

    selected = select_files(candidates, 10 * gb, 2, warnings)

    assert [row["file_id"] for row in selected] == ["A"]
    assert "knapsack_budget_exceeded" in warnings

# A test avoid exceed for total state limit
def test_knapsack_transition_budget_exceeded(monkeypatch):
    monkeypatch.setattr(knapsack_module, "MAX_DP_TRANSITIONS", 1)

    candidates = [
        {"file_id": "A", "size": 1 * gb, "read_rate": 10},
        {"file_id": "B", "size": 1 * gb, "read_rate": 9},
    ]

    with pytest.raises(KnapsackBudgetExceeded):
        select_files_knapsack(
            candidates, 2 * gb, 2, set()
        )

# A test indicate if integration really fallback
def test_strategy_falls_back_on_transition_budget(monkeypatch):
    monkeypatch.setattr(knapsack_module, "MAX_DP_TRANSITIONS", 1)

    candidates = [
        {"file_id": "A", "size": 6 * gb, "read_rate": 10},
        {"file_id": "B", "size": 5 * gb, "read_rate": 9},
        {"file_id": "C", "size": 5 * gb, "read_rate": 9},
    ]

    warnings = set()
    selected = select_files(candidates, 10 * gb, 2, warnings)

    assert [row["file_id"] for row in selected] == ["A"]
    assert "knapsack_budget_exceeded" in warnings

# An helper generate 3 files
def make_integration_payload():
    fixture = Path(__file__).parent / "fixtures" / "d2-temp-valid.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))

    data["mode_config"] = {
        "reserve_bytes": 0,
        "reserve_fraction": 0,
        "max_recommendations": 2
    }

    data["devices"][1]["free_bytes"] = 10 * gb

    base = data["history"]["file_activity"][0]

    files = [
        ("A", 6, 600),
        ("B", 5, 540),
        ("C", 5, 540)
    ]

    data["history"]["file_activity"] = [
        {
            **base,
            "file_id": file_id,
            "path": f"/mock/hdd-1/{file_id}.dat",
            "file_size_bytes": size * gb,
            "read_ops": reads
        }
        for file_id, size, reads in files
    ]

    return data

def test_policy_uses_knapsack():
    """Test Knap enabled"""
    data = make_integration_payload()

    result = evaluate_raid0_policy(**data)

    assert [row["file_id"] for row in result] == ["B", "C"]
    assert all(row["action"] == "move" for row in result)
    assert all(len(row) == 11 for row in result)

def test_policy_falls_back_to_greedy(monkeypatch):
    """Test fall back"""
    monkeypatch.setattr(knapsack_module, "MAX_DP_STATES", 1)

    data = make_integration_payload()

    result = evaluate_raid0_policy(**data)

    assert [row["file_id"] for row in result] == ["A"]
    assert all(row["action"] == "move" for row in result)
    assert all(len(row) == 11 for row in result)

if __name__ == "__main__":
    benchmark_knapsack()