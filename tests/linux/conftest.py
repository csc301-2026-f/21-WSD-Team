# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import sys
import types

if not sys.platform.startswith("linux"):
    collect_ignore_glob = ["test_*.py"]
else:
    try:
        import bcc  # noqa: F401  (real BCC available, e.g. on a dev machine)
    except ImportError:
        fake_bcc = types.ModuleType("bcc")

        class _UnavailableBPF:
            """Stand-in for bcc.BPF. Any real use fails like a missing tracer."""

            def __init__(self, *args, **kwargs):
                raise RuntimeError("BCC is not installed (test stand-in)")

            @staticmethod
            def support_kfunc():
                return False

        fake_bcc.BPF = _UnavailableBPF
        sys.modules["bcc"] = fake_bcc
