# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""D2 advice uses one SSD per evaluation; no shared-space identity is assumed."""
from ..common.recommendations import make_recommendation

def select_files_greedy(candidates, capacity, max_recommendations, warnings):
    """Select files using the original D2 greedy strategy.
       max_recommendations: the maximum number of suggestions given in one evaluation
    """
    selected = []
    remaining_space = capacity # remaining space on SSD
    sorted_candidates = sorted(candidates, key=lambda row: (
        -row.get("migration_score", row["read_rate"]), row["size"], row["file_id"]
    ))

    for row in sorted_candidates:

        # skip files without predicted migration benefit
        if row.get("migration_score", row["read_rate"]) <= 0:
            continue

        if row["size"] > remaining_space:
            warnings.add("insufficient_ssd_capacity")
            continue
        selected.append(row) # greedy select
        remaining_space = remaining_space - row["size"] # update remaining allocation budget

        if len(selected) >= max_recommendations: # too much advice
            break;
    return selected


def describe_scoring(row):
    """Describe the score actually used and return its matching constraint."""
    predicted_rate = row.get("predicted_read_rate")
    strategy = row.get(
        "prediction_strategy", "ml" if predicted_rate is not None else "latest"
    )
    spatial_factor = row.get("spatial_factor", 1.0)

    if strategy == "ml" and predicted_rate is not None:
        description = (
            f"Predicted read rate for the next 10 minutes: {predicted_rate:.6g} reads/s. "
        )
        method = "D4 ML-assisted file placement. "
        constraint = "d4_ml_migration_heuristic_unbenchmarked"
    elif strategy == "average":
        description = (
            f"Moving-average estimate for the next 10 minutes: "
            f"{row['estimated_read_rate']:.6g} reads/s. "
        )
        method = "D4 moving-average file placement. "
        constraint = "d4_moving_average_migration_heuristic_unbenchmarked"
    elif spatial_factor != 1.0:
        description = "Latest observed read rate with spatial scoring. "
        method = "D4 spatial file placement. "
        constraint = "d4_spatial_migration_heuristic_unbenchmarked"
    else:
        # Preserve the existing fallback and mock explanation, including its ID.
        return "D2 read-activity heuristic. ", "d2_read_activity_heuristic_unbenchmarked"

    if spatial_factor != 1.0:
        description += f"Spatial factor: {spatial_factor:.6g}. "
    description += f"Migration score: {row['migration_score']:.6g}. "
    return description + method, constraint


def select_recommendations(candidates, budgets, context, warnings,
                           *, execution_supported, selector=None):
    """Generate migration recommendations using the selected strategy."""

    if not budgets:
        return []

    # select one SSD target to avoid counting shared space twice
    target = min(budgets, key=lambda key: (-budgets[key], key))

    # use Knapsack or Greedy to select files
    selected = (selector or select_files_greedy)(
        candidates,
        budgets[target],
        context.config["max_recommendations"],
        warnings
    )

    result = []

    for row in selected:

        scoring_reason, scoring_constraint = describe_scoring(row)

        # common constraints for file migration
        constraints = [
            "approval_required",
            "executor_revalidate_identity_capacity_permissions_and_path_compatibility",
            "d2_single_ssd_target_per_evaluation",
            scoring_constraint
        ]

        # identify recommendations generated from mock data
        label = "MOCK: " if row["is_mock"] else ""

        if row["is_mock"]:
            constraints.append("mock_data_not_real_file_activity")

        # check whether file migration is supported
        if not execution_supported:
            constraints.append("file_move_execution_not_confirmed")

        # report the actual observed read activity
        reason = (
            f"{label}{row['file_id']}: "
            f"{row['read_ops']} reads ({row['read_rate']:.6g} reads/s). "
        )

        reason += scoring_reason

        # report the suggested migration target
        reason += (
            f"Consider {row['source']} -> {target}. "
            f"SSD speedup is unmeasured."
        )

        if not execution_supported:
            reason += (
                " Advice only; file-move execution support "
                "is not confirmed."
            )

        # generate recommendation using the existing API contract
        result.append(make_recommendation(
            timestamp=context.timestamp,
            reason=reason,
            file_id=row["file_id"],
            source_device_id=row["source"],
            target_device_id=target,
            constraints=constraints
        ))

    return result
