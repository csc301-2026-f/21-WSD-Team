"""This file is used to wire the existing modules. Host ID will be generated here."""
import sys
import uuid
from pathlib import Path

from backend.algorithms.algo01 import evaluate_raid0_policy
from backend.db.repository import SQLiteHistoryRepository
from .frontend_routes import register_frontend_routes
from .agent_adapter import LinuxAgentAdapter
from .algo_adapter import AlgorithmAdapter
from .db_adapter import DataBaseAdaptor
from .http_api import create_http_api
from .service import CoreService

def create_application(*, demo_mode=False, data_dir=None):
    # Chk data storage location
    if data_dir is None:
        directory = Path(__file__).resolve().parents[2] / ".wsd"
    else:
        directory = Path(data_dir)

    # Create one if not exist
    directory.mkdir(parents=True, exist_ok=True) 

    # Create Obj for Sahil's db
    real_db_path = directory / "wsd.db"
    real_repository = SQLiteHistoryRepository(str(real_db_path))

    # Read from saved settings
    settings = real_repository.get_settings()
    host_id = settings.get("host_id")

    # If first time to run our software, gen a new host id
    if not isinstance(host_id, str) or not host_id.strip():
        host_id = str(uuid.uuid4()) # random gen
        real_repository.save_settings({"host_id":host_id})

    # demo mode or real mode? select agent and db acrrodingly
    if demo_mode:
        active_repository = SQLiteHistoryRepository(str(directory / "wsd_demo.db"))
        agent = None

    else:
        if not sys.platform.startswith("linux"): # must be linux for D2
            raise RuntimeError("Real Mode is linux only for D2")

        from backend.linux.backend import LinuxBackend

        active_repository = real_repository
        linux_backend = LinuxBackend(host_id)
        agent = LinuxAgentAdapter(linux_backend)

    # Record wich data mode the db belongs
    mode = "demo" if demo_mode else "real"

    active_mode = active_repository.get_settings().get("data_mode")

    if active_mode not in (None, mode):
        raise ValueError("DB mode mismatch")
    active_repository.save_settings({"host_id":host_id, "data_mode":mode})

    # Adapter initilization
    database_adapter = DataBaseAdaptor(active_repository)
    algorithm_adapter = AlgorithmAdapter(evaluate_raid0_policy)

    capabilities = {
        "device_metrics": not demo_mode,
        "process_metrics": not demo_mode,
        "process_to_device_attribution": False,
        "file_access_metrics": demo_mode,
        "file_level_pooling": False,
        "ssd_caching": False,
        "file_move": False,
        "dry_run_action": False,
    }

    # Step 6: Initialize CORE
    core = CoreService(
        agent,
        algorithm_adapter,
        database_adapter,
        capabilities,
        host_id=host_id,
        demo_mode=demo_mode
    )

    # Step 7: Create HTTP application
    app = create_http_api(core)

    # Step 8: Serve Danny's frontend
    register_frontend_routes(app)

    return app, core