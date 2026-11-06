# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""A small English launcher; the existing frontend remains in the browser."""
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import uuid
import webbrowser

from runtime import data_directory


def worker_command(demo, directory, data_dir, port):
    executable = sys.executable
    if not getattr(sys, "frozen", False):
        # Do not show a second terminal when running the launcher from source.
        windowed = Path(executable).with_name("pythonw.exe")
        if windowed.exists():
            executable = str(windowed)
        arguments = [str(Path(__file__).with_name("entrypoint.py"))]
    else:
        arguments = []
    arguments += ["--worker", "--run-dir", str(directory), "--data-dir", str(data_dir),
                  "--parent-pid", str(os.getpid()), "--port", str(port)]
    if demo:
        arguments.append("--demo")
    return executable, arguments


class Worker:
    def __init__(self, demo, directory, data_dir, port):
        executable, arguments = worker_command(demo, directory, data_dir, port)
        self.process = self.handle = None
        if demo:
            self.process = subprocess.Popen(
                [executable, *arguments], creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            from win32com.shell import shell, shellcon
            result = shell.ShellExecuteEx(
                fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                lpVerb="runas", lpFile=executable,
                lpParameters=subprocess.list2cmdline(arguments), nShow=0,
            )
            self.handle = result["hProcess"]

    def running(self):
        if self.process is not None:
            return self.process.poll() is None
        import win32event
        return win32event.WaitForSingleObject(self.handle, 0) == win32event.WAIT_TIMEOUT

    def close(self):
        if self.handle is not None:
            self.handle.Close()
            self.handle = None


class Launcher:
    def __init__(self, root, args):
        self.root, self.args = root, args
        self.data_dir = (args.data_dir or data_directory()).resolve()
        self.worker = self.directory = self.mode = None
        self.pending_mode = None
        self.stopping = self.exiting = self.starting = False
        self.started_at = 0
        self.messages = queue.Queue()
        self.url = f"http://127.0.0.1:{args.port}/"
        root.title("Wise Storage Director")
        root.geometry("540x340")
        root.resizable(False, False)
        frame = ttk.Frame(root, padding=28)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Wise Storage Director", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Choose how to start WSD.").pack(anchor="w", pady=(6, 18))
        choices = ttk.Frame(frame)
        choices.pack(fill="x")
        self.real_button = ttk.Button(choices, text="Start Monitoring", command=lambda: self.start("real"))
        self.real_button.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.demo_button = ttk.Button(choices, text="Start Demo", command=lambda: self.start("demo"))
        self.demo_button.pack(side="left", expand=True, fill="x")
        ttk.Label(frame, text="Monitoring uses Administrator access. Demo uses sample data.",
                  wraplength=480).pack(anchor="w", pady=(12, 18))
        self.status = tk.StringVar(value="Status: Not running")
        ttk.Label(frame, textvariable=self.status, wraplength=480).pack(anchor="w")
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(20, 0))
        self.browser_button = ttk.Button(controls, text="Open Dashboard", state="disabled",
                                         command=lambda: webbrowser.open(self.url))
        self.browser_button.pack(side="left")
        ttk.Button(controls, text="Stop and Exit", command=self.exit).pack(side="right")
        ttk.Label(frame, text="No files are moved automatically.").pack(anchor="w", pady=(16, 0))
        root.protocol("WM_DELETE_WINDOW", self.exit)
        root.after(200, self.poll)
        if args.demo:
            root.after(100, lambda: self.start("demo"))

    def buttons(self, enabled):
        for button in (self.real_button, self.demo_button):
            button.configure(state="normal" if enabled else "disabled")

    def start(self, mode):
        if self.starting or self.stopping or self.exiting:
            return
        if self.worker is not None:
            if self.mode == mode:
                webbrowser.open(self.url)
            else:
                self.pending_mode = mode
                self.stop()
            return
        try:
            with socket.socket() as connection:
                connection.bind(("127.0.0.1", self.args.port))
        except OSError:
            messagebox.showerror("WSD cannot start", f"Port {self.args.port} is already in use. "
                                 "Stop the other application before starting WSD.")
            return
        self.directory = self.data_dir / "sessions" / uuid.uuid4().hex
        self.directory.mkdir(parents=True, exist_ok=True)
        self.mode, self.starting = mode, True
        self.started_at = time.monotonic()
        self.buttons(False)
        self.status.set("Status: Starting demo..." if mode == "demo" else
                        "Status: Waiting for Administrator approval...")

        def spawn():
            try:
                worker = Worker(mode == "demo", self.directory, self.data_dir, self.args.port)
                self.messages.put((worker, None))
            except Exception as error:
                self.messages.put((None, str(error)))
        threading.Thread(target=spawn, daemon=True).start()

    def stop(self):
        self.stopping = True
        self.started_at = time.monotonic()
        self.buttons(False)
        self.browser_button.configure(state="disabled")
        self.status.set("Status: Stopping...")
        (self.directory / "stop").touch()

    def exit(self):
        self.exiting = True
        self.pending_mode = None
        if self.worker is not None or self.starting:
            self.stop()
        else:
            self.root.destroy()

    def poll(self):
        try:
            worker, error = self.messages.get_nowait()
        except queue.Empty:
            pass
        else:
            self.worker = worker
            if error:
                self.starting = False
                self.buttons(True)
                self.status.set("Status: Not running")
                if not self.exiting:
                    messagebox.showerror("WSD could not start", "Startup was cancelled or failed.\n\n" + error)
                else:
                    self.root.destroy()
                    return
        if self.worker is not None:
            try:
                state = json.loads((self.directory / "status.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                state = {}
            if not self.worker.running():
                was_stopping = self.stopping
                self.worker.close()
                self.worker = None
                self.starting = self.stopping = False
                self.buttons(True)
                self.browser_button.configure(state="disabled")
                self.status.set("Status: Not running")
                if state.get("state") == "error":
                    self.pending_mode = None
                if (not was_stopping or state.get("state") == "error") and not self.exiting:
                    messagebox.showerror("WSD stopped", state.get("message", "The backend exited unexpectedly.")
                                         + f"\n\nLog: {self.directory / 'backend.log'}")
                if self.exiting:
                    self.root.destroy()
                    return
                if self.pending_mode:
                    mode, self.pending_mode = self.pending_mode, None
                    self.start(mode)
            elif self.starting and state.get("state") == "running" and not self.stopping:
                self.starting = False
                self.status.set("Status: Demo running (sample data)" if self.mode == "demo" else
                                "Status: Monitoring running (real data)")
                self.buttons(True)
                self.browser_button.configure(state="normal")
                webbrowser.open(self.url)
            elif time.monotonic() - self.started_at > 30 and (self.starting or self.stopping):
                self.status.set("Status: Still stopping; please keep this window open." if self.stopping else
                                "Status: Still starting; check Administrator approval.")
        self.root.after(200, self.poll)


def launch(args):
    if sys.platform != "win32":
        raise SystemExit("This launcher requires Windows.")
    root = tk.Tk()
    ttk.Style(root).theme_use("vista")
    Launcher(root, args)
    root.mainloop()
