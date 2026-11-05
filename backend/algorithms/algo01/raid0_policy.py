# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""D2 recommendation-only entry using the current shared record fields.

All timestamps and identities come from inputs. No OS calls, SQL, clock reads,
file moves, RAID creation or SSD-cache execution are performed here.
"""
from ..common.capacity import index_devices, build_ssd_budgets
from ..common.recommendations import make_none
from ..common.validation import is_mock_source
from .inputs import PolicyInputError, validate_inputs
from .candidates import collect_candidates
from .greedy_selection import select_recommendations
from .strategy_controller import select_files


def _has_mock_activity(history):
    rows = history.get("file_activity", []) if isinstance(history, dict) else []
    return isinstance(rows, list) and any(isinstance(row, dict) and is_mock_source(row.get("source")) for row in rows)


def evaluate_raid0_policy(devices: list[dict], realtime: dict, history: dict,
                          mode_config: dict, capabilities: dict) -> list[dict]:
    """Return eleven-field advice records; execution capability is a separate concern."""
    try:
        context = validate_inputs(devices, realtime, history, mode_config, capabilities)
    except PolicyInputError as error:
        if error.timestamp is None:
            raise
        return [make_none(error.timestamp, error.code, is_mock=_has_mock_activity(history))]
    warnings = set()
    try:
        device_map = index_devices(devices, context.host, warnings)
    except ValueError:
        return [make_none(context.timestamp, "duplicate_device_id", is_mock=_has_mock_activity(history))]
    budgets = build_ssd_budgets(device_map, context.config["reserve_bytes"], context.config["reserve_fraction"])
    if not context.activity:
        warnings.add("missing_file_activity")
    if not budgets:
        warnings.add("no_eligible_ssd")
    candidates = collect_candidates(context, device_map, warnings)
    result = select_recommendations(candidates, budgets, context, warnings,
    execution_supported=capabilities.get("file_move") is True,
    selector=select_files)
    return result or [make_none(context.timestamp, "no_eligible_recommendation", sorted(warnings),
        is_mock=_has_mock_activity(history))]
