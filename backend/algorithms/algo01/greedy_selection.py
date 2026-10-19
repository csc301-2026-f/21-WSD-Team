"""D2 advice uses one SSD per evaluation; no shared-space identity is assumed."""
from ..common.recommendations import make_recommendation


def select_recommendations(candidates, budgets, context, warnings, *, execution_supported):
    """Use one target budget, deducting whole-file sizes across the entire result."""
    if not budgets:
        return []
    # Current Device records cannot distinguish independent drives from aliases.
    # Selecting one target avoids counting the same underlying space twice.
    target = min(budgets, key=lambda key: (-budgets[key], key))
    remaining = budgets[target]
    result = []
    for row in candidates:
        if row["size"] > remaining:
            warnings.add("insufficient_ssd_capacity")
            continue
        constraints = ["approval_required", "executor_revalidate_identity_capacity_permissions_and_path_compatibility",
            "d2_read_activity_heuristic_unbenchmarked", "d2_single_ssd_target_per_evaluation"]
        label = "MOCK: " if row["is_mock"] else ""
        if row["is_mock"]:
            constraints.append("mock_data_not_real_file_activity")
        if not execution_supported:
            constraints.append("file_move_execution_not_confirmed")
        reason = (f"{label}{row['file_id']}: {row['read_ops']} reads ({row['read_rate']:.6g} reads/s). "
            f"Consider {row['source']} -> {target}. D2 read-activity heuristic; SSD speedup is unmeasured.")
        if not execution_supported:
            reason += " Advice only; file-move execution support is not confirmed."
        result.append(make_recommendation(timestamp=context.timestamp, reason=reason,
            file_id=row["file_id"], source_device_id=row["source"], target_device_id=target,
            constraints=constraints))
        remaining -= row["size"]
        if len(result) >= context.config["max_recommendations"]:
            break
    return result
