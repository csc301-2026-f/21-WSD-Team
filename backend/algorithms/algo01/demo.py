# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Run invented D2 records. Never collect activity or execute a storage action."""
import argparse
import json
import sys
from pathlib import Path
from .raid0_policy import evaluate_raid0_policy
from ..common.validation import is_mock_source


def main(argv=None):
    parser = argparse.ArgumentParser(description="MOCK ONLY: D2 recommendation example")
    parser.add_argument("--mock-input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.mock_input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"devices", "realtime", "history", "mode_config", "capabilities"}:
            raise ValueError("expected the five policy arguments")
        if any(not isinstance(row, dict) or not is_mock_source(row.get("source")) for row in payload["history"].get("file_activity", [])):
            raise ValueError("mock examples must label each FileActivity source as mock or mock:<description>")
        items = evaluate_raid0_policy(**payload)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        print("MOCK demo input error: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps({"data_kind": "MOCK", "storage_actions_executed": False,
                      "recommendations": items}, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
