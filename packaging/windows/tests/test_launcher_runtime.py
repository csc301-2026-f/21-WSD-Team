# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Exercise real demo workers without starting Windows ETW collection."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
ENTRY = ROOT / "packaging/windows/entrypoint.py"


@unittest.skipUnless(sys.platform == "win32", "Windows launcher")
class LauncherRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="wsd launcher test ")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.session = self.directory / "session"
        self.session.mkdir()
        with socket.socket() as connection:
            connection.bind(("127.0.0.1", 0))
            self.port = connection.getsockname()[1]

    def command(self, parent=None):
        return [sys.executable, "-B", str(ENTRY), "--worker", "--demo",
                "--run-dir", str(self.session), "--data-dir", str(self.directory / "data"),
                "--parent-pid", str(parent or os.getpid()), "--port", str(self.port)]

    def start_worker(self):
        process = subprocess.Popen(self.command(), cwd=ROOT)
        def cleanup():
            (self.session / "stop").touch()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self.addCleanup(cleanup)
        return process

    def wait_state(self, expected):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                status = json.loads((self.session / "status.json").read_text())
                if status["state"] == expected:
                    return status
                if status["state"] == "error" and expected != "error":
                    self.fail(status)
            except (OSError, ValueError):
                pass
            time.sleep(0.1)
        self.fail(f"Worker did not reach {expected}")

    def test_demo_serves_frontend_recommendations_and_stops(self):
        worker = self.start_worker()
        self.wait_state("running")
        base = f"http://127.0.0.1:{self.port}"
        with urlopen(base + "/", timeout=5) as response:
            self.assertIn(b"Wise Storage Director", response.read())
        request = Request(base + "/api/v1/recommendations/refresh", method="POST")
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read())
        self.assertIn("MOCK", json.dumps(result))
        self.assertIn('"move"', json.dumps(result))
        (self.session / "stop").touch()
        self.assertEqual(worker.wait(timeout=10), 0)
        self.wait_state("stopped")
        with socket.socket() as connection:
            self.assertNotEqual(connection.connect_ex(("127.0.0.1", self.port)), 0)

    def test_occupied_port_reports_failure_and_does_not_start(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", self.port))
            listener.listen()
            worker = self.start_worker()
            self.wait_state("error")
            self.assertNotEqual(worker.wait(timeout=10), 0)

    def test_worker_exits_if_launcher_disappears(self):
        import psutil
        parent_code = (
            "import json,os,subprocess,sys,time; "
            "args=json.loads(sys.argv[1]); "
            "args[args.index('--parent-pid')+1]=str(os.getpid()); "
            "p=subprocess.Popen(args); "
            "print(p.pid,flush=True); "
            "time.sleep(60)"
        )
        parent = subprocess.Popen([sys.executable, "-c", parent_code, json.dumps(self.command())],
                                  stdout=subprocess.PIPE, text=True, cwd=ROOT)
        self.addCleanup(parent.stdout.close)
        self.addCleanup(lambda: parent.poll() is None and parent.kill())
        child = psutil.Process(int(parent.stdout.readline()))
        def cleanup_child():
            if child.is_running():
                child.kill()
                child.wait(timeout=5)
        self.addCleanup(cleanup_child)
        self.wait_state("running")
        parent.terminate()
        parent.wait(timeout=5)
        child.wait(timeout=10)
        self.wait_state("stopped")


if __name__ == "__main__":
    unittest.main()
