# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Run the existing CORE until the launcher requests a stop or exits."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import traceback


def data_directory():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "WSD"


def write_status(directory, state, **details):
    temporary = directory / "status.tmp"
    temporary.write_text(json.dumps({"state": state, **details}), encoding="utf-8")
    temporary.replace(directory / "status.json")


def shutdown(core, collector, server, directory, owns_logger, log):
    """Bound shutdown if the Windows ETW consumer blocks while joining its thread."""
    errors = []
    def close():
        try:
            if server is not None:
                server.server_close()
            if collector is not None:
                collector.stop()
            if core is not None:
                core.close()
        except Exception as error:
            traceback.print_exc()
            errors.append(str(error))
    cleanup = threading.Thread(target=close, daemon=True)
    cleanup.start()
    cleanup.join(timeout=10)
    if cleanup.is_alive():
        # Stop only a logger this worker created, never an existing trace session.
        import faulthandler
        faulthandler.dump_traceback(file=log)
        try:
            if owns_logger:
                subprocess.run(["logman", "stop", "NT Kernel Logger", "-ets"],
                               capture_output=True, check=False, timeout=5,
                               creationflags=subprocess.CREATE_NO_WINDOW)
                query = subprocess.run(["logman", "query", "NT Kernel Logger", "-ets"],
                                       capture_output=True, timeout=5,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                if query.returncode == 0:
                    raise RuntimeError("Windows tracing did not stop.")
            write_status(directory, "stopped")
            log.write("Shutdown timed out after 10 seconds; ending the isolated worker.\n")
            log.flush()
            os._exit(0)
        except Exception as error:
            write_status(directory, "error", message=f"Could not stop monitoring: {error}")
            log.flush()
            os._exit(1)
    if errors:
        raise RuntimeError(errors[0])


def run_backend(args):
    import psutil
    from werkzeug.serving import make_server
    from backend.core.bootstrap import create_application
    from backend.core.collector_agent import CollectorAgent

    directory = args.run_dir
    directory.mkdir(parents=True, exist_ok=True)
    core = collector = server = None
    owns_logger = False
    exit_code = 0
    with (directory / "backend.log").open("a", encoding="utf-8", buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            parent = psutil.Process(args.parent_pid)
            # Process objects also check creation time, so a reused PID is not our launcher.
            parent.create_time()
            app, core = create_application(
                demo_mode=args.demo, data_dir=args.data_dir or data_directory(),
            )
            # Reserve the HTTP port before starting a real ETW session.
            server = make_server("127.0.0.1", args.port, app, threaded=True)
            server.timeout = 0.25
            core.start()
            if not args.demo:
                session = core.agent.backend.etw_source._transport._session
                owns_logger = not session.provider.kernel_trace_was_running
                collector = CollectorAgent(core, interval_seconds=1)
                collector.start()
            write_status(directory, "running", pid=os.getpid())
            while parent.is_running() and not (directory / "stop").exists():
                server.handle_request()
        except (Exception, SystemExit) as error:
            traceback.print_exc()
            write_status(directory, "error", message=str(error))
            exit_code = 1
        finally:
            try:
                shutdown(core, collector, server, directory, owns_logger, log)
            except Exception as error:
                traceback.print_exc()
                write_status(directory, "error", message=f"Could not stop monitoring: {error}")
                exit_code = 1
            if exit_code == 0:
                write_status(directory, "stopped")
            # Windowed Python has no console streams to restore; keep the log valid
            # while the interpreter finishes shutting down imported libraries.
            sys.stdout = sys.stderr = sys.__stderr__
    return exit_code
