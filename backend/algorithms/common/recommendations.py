# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""The current contract's eleven fields only. No v2 record extensions."""
import hashlib
import json
from .validation import is_text, parse_utc

FIELDS = frozenset(("recommendation_id", "mode", "action", "file_id", "source_device_id",
    "target_device_id", "reason", "created_at_utc", "requires_approval", "estimated_benefit", "constraints"))


def make_recommendation(*, timestamp, reason, file_id=None, source_device_id=None,
                        target_device_id=None, constraints=()):
    """Build a move or global none with a deterministic record ID."""
    parse_utc(timestamp)
    ids = (file_id, source_device_id, target_device_id)
    move = any(value is not None for value in ids)
    if move and (not all(is_text(value) for value in ids) or source_device_id == target_device_id):
        raise ValueError("move requires a file and distinct source/target IDs")
    if not is_text(reason):
        raise ValueError("reason is required")
    item = {"mode": "raid0", "action": "move" if move else "none", "file_id": file_id,
        "source_device_id": source_device_id, "target_device_id": target_device_id,
        "reason": reason, "created_at_utc": timestamp, "requires_approval": move,
        "estimated_benefit": None, "constraints": sorted(set(constraints))}
    digest = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
    return {"recommendation_id": "raid0-" + digest[:24], **item}


def make_none(timestamp, code, details=(), *, is_mock=False):
    """An evaluation-wide explanation; no file or device identity is fabricated."""
    return make_recommendation(timestamp=timestamp, reason=("MOCK: " if is_mock else "") + code,
        constraints=(code, *details, *( ("mock_data_not_real_file_activity",) if is_mock else () )))
