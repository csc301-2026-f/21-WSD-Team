# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only

from .knapsack_selection import (
    select_files_knapsack,
    KnapsackBudgetExceeded
)
from .greedy_selection import select_files_greedy


def select_files(candidates, capacity, max_recommendations, warnings):
    """Prefer exact Knapsack, fall back to Greedy if the DP budget is exceeded."""
    try:
        return select_files_knapsack(
            candidates,
            capacity,
            max_recommendations,
            warnings
        )

    except KnapsackBudgetExceeded:
        warnings.add("knapsack_budget_exceeded")

        return select_files_greedy(
            candidates,
            capacity,
            max_recommendations,
            warnings
        )