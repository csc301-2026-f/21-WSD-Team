# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Frozen Linux launcher; reuse the existing backend and keep user data separate."""
import os
from pathlib import Path
import shutil
import signal
import sys

VERSION = "1.0.0"


def main():
    if sys.argv[1:] == ["--version"]:
        print(f"Wise Storage Director {VERSION} (Linux x86-64, D2)")
        return 0
    if not any(arg == "--data-dir" or arg.startswith("--data-dir=")
               for arg in sys.argv[1:]):
        data_home = os.environ.get("XDG_DATA_HOME")
        root = Path(data_home) if data_home else Path.home() / ".local/share"
        sys.argv.extend(["--data-dir", str(root / "wsd")])
    if "--demo" not in sys.argv and not any(arg in ("-h", "--help") for arg in sys.argv):
        if not shutil.which("lsblk") or not Path("/proc/diskstats").is_file():
            print("Real Mode requires Linux /proc and lsblk (util-linux).", file=sys.stderr)
            return 1

    def stop(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    print(f"WSD {VERSION}: {'MOCK DEMO (US-05)' if '--demo' in sys.argv else 'REAL COLLECTION (US-01/02)'}", flush=True)
    from backend.main import main as backend_main
    backend_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
