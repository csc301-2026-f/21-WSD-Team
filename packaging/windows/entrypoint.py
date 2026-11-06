# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Windows GUI entry point and its private backend worker."""
import argparse
import sys
from pathlib import Path

# Allow this file to run from a source checkout as well as a frozen executable.
ROOT = Path(__file__).resolve().parents[2]
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description="Wise Storage Director")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--run-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--parent-pid", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    if args.worker:
        if args.run_dir is None or args.parent_pid is None:
            parser.error("The worker needs a launcher session.")
        from runtime import run_backend
        return run_backend(args)
    from launcher import launch
    launch(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
