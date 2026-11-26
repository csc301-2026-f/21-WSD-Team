# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from datetime import datetime, timezone
from backend.algorithms.algo02.greedy_selection import select_files_greedy, select_recommendations
from backend.algorithms.algo02.inputs import D2Inputs

def test_greedy_sorts_candidates_by_read_density():
    """Test even if frenquency is not guaranteed by order, greedy algo still pick most frequently read"""
    gb = 1024 ** 3

    candidates = [
        {"file_id": "A", "read_rate": 1.0, "size": 1 * gb},
        {"file_id": "B", "read_rate": 10.0, "size": 4 * gb},
        {"file_id": "C", "read_rate": 5.0, "size": 3 * gb},
    ]

    selected = select_files_greedy(candidates, 5*gb, 2, set())
    assert [row["file_id"] for row in selected] == ["B", "A"]


def test_greedy_packs_smaller_high_density_files_over_giant_file():
    """Smaller hot files should be favored over a single giant file that exhausts cache space."""
    mb = 1024 ** 2
    candidates = [
        {"file_id": "giant-archive", "read_rate": 5.0, "size": 900 * mb},
        {"file_id": "hot-index-1", "read_rate": 3.0, "size": 10 * mb},
        {"file_id": "hot-index-2", "read_rate": 2.5, "size": 10 * mb},
    ]

    selected = select_files_greedy(candidates, 100 * mb, 5, set())
    assert [row["file_id"] for row in selected] == ["hot-index-1", "hot-index-2"]


def test_select_recommendations_populates_ml_benefit_and_constraints():
    """Verify ML scores and estimated benefits are attached to recommendation records."""
    context = D2Inputs(
        now=datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc),
        timestamp="2026-10-17T12:00:00Z",
        host="mock-host",
        config={"max_recommendations": 5},
        activity=[],
    )
    candidates = [
        {
            "file_id": "db-index",
            "source": "hdd-1",
            "size": 4 * 1024 ** 2,
            "read_ops": 120,
            "read_rate": 2.0,
            "is_mock": False,
            "ml_cache_prob": 0.88,
            "estimated_benefit_ms": 8817.6,
        }
    ]
    budgets = {"ssd-1": 1024 ** 3}
    warnings = set()

    recs = select_recommendations(candidates, budgets, context, warnings, execution_supported=True)
    assert len(recs) == 1
    assert recs[0]["action"] == "cache"
    assert recs[0]["estimated_benefit"] == "8817.6 ms saved / 10 min (p=0.88)"
    assert "d4_ml_logistic_cache_scorer" in recs[0]["constraints"]
    assert "cache_population_execution_not_confirmed" not in recs[0]["constraints"]