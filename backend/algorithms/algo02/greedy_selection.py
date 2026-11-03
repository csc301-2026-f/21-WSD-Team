# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""D2 advice for SSD caching uses one cache target per evaluation; original files remain intact."""
from ..common.recommendations import make_recommendation


def select_files_greedy(candidates, capacity, max_recommendations, warnings):
    """Select files for SSD caching using the greedy strategy.
       max_recommendations: the maximum number of suggestions given in one evaluation
    """
    selected = []
    remaining_space = capacity
    sorted_candidates = sorted(candidates, key=lambda row: (-row["read_rate"], row["size"], row["file_id"]))

    for row in sorted_candidates:
        if row["size"] > remaining_space:
            warnings.add("insufficient_ssd_capacity")
            continue
        selected.append(row)
        remaining_space -= row["size"]

        if len(selected) >= max_recommendations:
            break
    return selected


def select_recommendations(candidates, budgets, context, warnings, *, execution_supported, selector=None):
    """Use one target cache budget, deducting file sizes for cache population across the result."""
    if not budgets:
        return []
    
    # Select one target SSD cache device based on available budget space.
    target = min(budgets, key=lambda key: (-budgets[key], key))
    
    # Use the provided custom selector or fall back to the default greedy selector
    selected = (selector or select_files_greedy)(
        candidates,
        budgets[target],
        context.config["max_recommendations"],
        warnings
    )

    result = []
    for row in selected:
        constraints = [
            "approval_required",
            "executor_revalidate_identity_capacity_permissions_and_path_compatibility",
            "d2_read_activity_heuristic_unbenchmarked",
            "d2_single_ssd_target_per_evaluation",
            "cache_preserves_original_source_file"
        ]
        
        label = "MOCK: " if row["is_mock"] else ""
        if row["is_mock"]:
            constraints.append("mock_data_not_real_file_activity")
        if not execution_supported:
            constraints.append("cache_population_execution_not_confirmed")
            
        # Tailor the reason text for caching instead of file moving
        reason = (
            f"{label}{row['file_id']}: {row['read_ops']} reads ({row['read_rate']:.6g} reads/s). "
            f"Consider caching {row['source']} -> {target} (original file retained). "
            f"D2 read-activity heuristic; SSD cache speedup is unmeasured."
        )
        if not execution_supported:
            reason += " Advice only; cache population execution support is not confirmed."
            
        result.append(make_recommendation(
            timestamp=context.timestamp,
            reason=reason,
            file_id=row["file_id"],
            source_device_id=row["source"],
            target_device_id=target,
            constraints=constraints,
            mode="ssd_caching"  # Explicitly passes the required mode for ALGO-02
        ))
            
    return result