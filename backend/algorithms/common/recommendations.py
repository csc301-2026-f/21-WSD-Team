# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""The current contract's eleven fields only. No v2 record extensions."""
"""The current contract's eleven fields only. No v2 record extensions."""
import hashlib
import json
from .validation import is_text, parse_utc

FIELDS = frozenset(("recommendation_id", "mode", "action", "file_id", "source_device_id",
    "target_device_id", "reason", "created_at_utc", "requires_approval", "estimated_benefit", "constraints"))

VALID_MODES = {"raid0", "ssd_caching"}
VALID_ACTIONS = {
    "raid0": {"move", "none"},
    "ssd_caching": {"cache", "none"}
}


def make_recommendation(*, timestamp, reason, file_id=None, source_device_id=None,
                        target_device_id=None, constraints=(), mode="raid0", action=None):
    """Build a move, cache, or global none with a deterministic record ID."""
    parse_utc(timestamp)

    # 1. Validate mode string
    if not is_text(mode) or mode not in VALID_MODES:
        raise ValueError(f"Invalid mode: '{mode}'. Must be one of {sorted(VALID_MODES)}")

    ids = (file_id, source_device_id, target_device_id)
    has_target_info = any(value is not None for value in ids)
    
    if has_target_info and (not all(is_text(value) for value in ids) or source_device_id == target_device_id):
        raise ValueError("recommendation requires a file and distinct source/target IDs")
    
    if not is_text(reason):
        raise ValueError("reason is required")
        
    # Automatically set action based on mode if not explicitly provided
    if action is None:
        if has_target_info:
            action = "move" if mode == "raid0" else "cache"
        else:
            action = "none"

    # 2. Validate action against mode
    if action not in VALID_ACTIONS[mode]:
        raise ValueError(f"Invalid action '{action}' for mode '{mode}'. Allowed: {sorted(VALID_ACTIONS[mode])}")

    # 3. Ensure consistency between action and target info
    if action == "none" and has_target_info:
        raise ValueError("Action 'none' cannot include file or device target information.")

    if action in {"move", "cache"} and not has_target_info:
        raise ValueError(f"Action '{action}' requires file and target info but none was provided.")

    item = {
        "mode": mode,
        "action": action, 
        "file_id": file_id,
        "source_device_id": source_device_id,
        "target_device_id": target_device_id,
        "reason": reason,
        "created_at_utc": timestamp,
        "requires_approval": has_target_info,
        "estimated_benefit": None, 
        "constraints": sorted(set(constraints))
    }
    
    digest = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
    return {"recommendation_id": f"{mode}-{digest[:24]}", **item}

def make_none(timestamp, code, details=(), *, is_mock=False, mode="raid0"):
    """An evaluation-wide explanation; no file or device identity is fabricated."""
    return make_recommendation(
        timestamp=timestamp, 
        reason=("MOCK: " if is_mock else "") + code,
        constraints=(code, *details, *( ("mock_data_not_real_file_activity",) if is_mock else () )),
        mode=mode,
        action="none"
    )
