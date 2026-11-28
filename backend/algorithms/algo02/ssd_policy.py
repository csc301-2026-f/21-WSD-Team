"""D3 SSD caching recommendation-only entry point."""
from ..common.capacity import index_devices, build_ssd_budgets
from ..common.recommendations import make_none
from ..common.validation import is_mock_source
from .inputs import PolicyInputError, validate_inputs
from .candidates import collect_candidates
from .greedy_selection import select_recommendations
from .prediction import score_cache_candidates

def _has_mock_activity(history):
    rows = history.get("file_activity", []) if isinstance(history, dict) else []
    return isinstance(rows, list) and any(isinstance(row, dict) and is_mock_source(row.get("source")) for row in rows)

def evaluate_ssd_caching_policy(devices: list[dict], realtime: dict, history: dict,
                        mode_config: dict, capabilities: dict) -> list[dict]:
    """Evaluate SSD caching recommendations based on file read heat and cache constraints."""
    try:
        context = validate_inputs(devices, realtime, history, mode_config, capabilities)
    except PolicyInputError as error:
        if error.timestamp is None:
            raise
        return [make_none(error.timestamp, error.code, is_mock=_has_mock_activity(history), mode="ssd_caching")]
        
    warnings = set()
    try:
        device_map = index_devices(devices, context.host, warnings)
    except ValueError:
        return [make_none(context.timestamp, "duplicate_device_id", is_mock=_has_mock_activity(history), mode="ssd_caching")]
        
    budgets = build_ssd_budgets(device_map, context.config["reserve_bytes"], context.config["reserve_fraction"])
    if not context.activity:
        warnings.add("missing_file_activity")
    if not budgets:
        warnings.add("no_eligible_ssd")

    raw_candidates = collect_candidates(context, device_map, warnings)
    scored_candidates = score_cache_candidates(raw_candidates, context.activity)
    min_cache_prob = context.config["min_cache_prob"]
    goal = context.config["goal"]
    eligible_candidates = []
    
    for row in scored_candidates:
        if goal == "lifespan" and row.get("write_ops", 0) > 0:
            warnings.add("skipped_write_active_for_lifespan")
            continue
        if row["ml_cache_prob"] < min_cache_prob:
            warnings.add("below_ml_cache_threshold")
            continue
        eligible_candidates.append(row)

    result = select_recommendations(
        eligible_candidates, budgets, context, warnings,
        execution_supported=capabilities.get("file_cache") is True or capabilities.get("file_move") is True
    )
    return result or [make_none(
        context.timestamp, "no_eligible_recommendation", sorted(warnings),
        is_mock=_has_mock_activity(history), mode="ssd_caching"
    )]