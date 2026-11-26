# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from datetime import datetime, timezone, timedelta
from .demo_data import load_demo_input
from backend.linux.models import ErrorCode
from .agent_adapter import LinuxAgentAdapter
import logging
import os
import uuid
logger = logging.getLogger(__name__)

class CoreService:
    def __init__(self, agent, algorithm, database, capabilities=None, demo_mode = False, host_id = None):
        self.agent = agent
        self.algorithm = algorithm
        self.database = database
        self.capabilities = capabilities
        self.demo_mode = demo_mode
        self.host_id = host_id
        self.track_folders = {}
        self.movements = {}

    def start(self)-> None:
        if not self.demo_mode:
            result = self.agent.start()
            if isinstance(self.agent, LinuxAgentAdapter):
                self.capabilities["file_access_metrics"] = result is None
            subscriptions = self.database.list_file_subscriptions("active")
            for sub in subscriptions:
                if sub["target_type"] == "file":
                    self.agent.track_file(sub["path"])
                elif sub["target_type"] == "folder":
                    self.agent.track_folder(sub["path"])

    def close(self) -> None:
        if not self.demo_mode:
            self.agent.close()

    def collect_and_record(self) -> None:
        """
        Collect one snapshot of device and process I/O data and persist it to database.

        flow: Agent -> CORE -> DB
        """
        if not self.demo_mode:
            devices = self.agent.get_devices()
            self.database.upsert_devices(devices)
            device_metric = self.agent.get_device_metrics()
            self.database.ingest_device_metrics(device_metric)
            process_metric = self.agent.get_process_metrics()
            self.database.ingest_process_metrics(process_metric)

    def check_history_record(self):
        ######## Not for D2
        pass

    def get_devices(self):
        if self.demo_mode:
            demo_data = load_demo_input(self.host_id)
            return demo_data["devices"]
        return self.agent.get_devices()

    def get_current_device_metrics(self):
        if self.demo_mode:
            return []
        return self.agent.get_device_metrics()

    def get_recommendations(self, mode=None):
        return self.database.list_recommendations(mode)

    def get_capabilities(self):
        if self.demo_mode:
            demo_data = load_demo_input(self.host_id)
            return demo_data["capabilities"]
        return self.capabilities

    def get_current_process_activity(self):
        """
        Return current per-process I/O activity.

        Flow: Agent -> CORE -> HTTP/UI
        User Story: US-01
        """
        if self.demo_mode:
            return []
        return self.agent.get_process_metrics()

    def get_current_file_activity(self):
        """
        Return current file activity for display.

        Flow: Agent -> CORE -> HTTP/UI
        """
        if self.demo_mode:
            return []
        return self.agent.get_file_activity(8)

    def save_current_file_activity(self):
        """
        Save current file activity to the database

        Flow: Agent -> CORE -> DB
        """
        if not self.demo_mode:
            file_activity = self.agent.get_file_activity(60)
            self.database.ingest_file_activity(file_activity)

    def get_historical_process_activity(self, process_instance_ids, start_utc,
                                        end_utc, bucket_seconds = None):
        """
        Return historical I/O activity for selected process instances.

        Flow: DB -> CORE -> HTTP/UI
        User Story: US-02
        """
        return self.database.query_process_history(process_instance_ids, start_utc, end_utc, bucket_seconds)

    def refresh_recommendation(self, mode = None):
        """
        Build new storage recommendations using current and historical data.

        Flow: Agent + DB -> CORE -> Algorithm -> DB / HTTP/UI
        User Story: US-05
        """
        if self.demo_mode:
            demo_data = load_demo_input(self.host_id)
            devices = demo_data["devices"]
            realtime = demo_data["realtime"]
            history = demo_data["history"]
            mode_config = demo_data["mode_config"]
            capabilities = demo_data["capabilities"]
        else:
            devices = self.agent.get_devices()
            host_id = None
            if devices:
                host_id = devices[0].get("host_id")
            current = datetime.now(timezone.utc)
            start_utc = (current - timedelta(minutes = 60)).isoformat().replace("+00:00", "Z")
            end_utc = current.isoformat().replace("+00:00", "Z")
            file_activity = self.database.query_file_activity_windows(start_utc, end_utc)

            # Generate evaluation time AFTER collecting file activity
            evaluation_time_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            realtime = {
                "host_id": host_id,
                "evaluation_time_utc": evaluation_time_utc
            }

            history={"file_activity": file_activity}
            mode_config= {} #Not required in D2
            capabilities = self.capabilities or {} #TODO agent not done

        # Check mode to use
        if mode == "ssd_caching":
            recommendations =self.algorithm.evaluate_ssd(devices, realtime, history, mode_config, capabilities)
        else:
            recommendations =self.algorithm.evaluate_raid0(devices, realtime, history, mode_config, capabilities)
        self.database.save_recommendations(recommendations)
        return recommendations

    def track_file(self, path):
        """
        Start tracking a file and save its subscription to the database.

        Flow: Agent -> CORE -> DB
        """
        file = self.agent.track_file(path)
        path = os.path.normpath(path)
        self.database.upsert_file_subscription({"subscription_id": None,        #TODO not yet decided
                                                "host_id": self.host_id,
                                                "path": path,
                                                "target_type": "file",
                                                "status": "active"})
        return file

    def track_folder(self, path):
        """
        Start tracking a folder and save its subscription to the database.

        Flow: Agent -> CORE -> DB
        """
        folder = self.agent.track_folder(path)
        path = os.path.normpath(path)
        self.track_folders[path] = folder
        self.database.upsert_file_subscription({"subscription_id": None,        #TODO not yet decided
                                                "host_id": self.host_id,
                                                "path": path,
                                                "target_type": "folder",
                                                "status": "active"})
        return folder

    def list_file_subscriptions(self, status = "active"):
        """
        Return file and folder subscriptions

        Flow: DB -> CORE -> HTTP/UI
        """
        return self.database.list_file_subscriptions(status)

    def untrack_file(self, file):
        """
        Untracking a file and save its subscription to the database.

        Flow: Agent -> CORE -> DB
        """
        path = file.absolute_path
        file = self.agent.untrack_file(file)
        self.database.upsert_file_subscription({"subscription_id": None,        #TODO not yet decided
                                                "host_id": self.host_id,
                                                "path": path,
                                                "target_type": "file",
                                                "status": "removed"})

    def untrack_folder(self, files):
        """
        Untracking a folder and save its subscription to the database.

        Flow: Agent -> CORE -> DB
        """
        path = [key for key, value in self.track_folders.items() if value == files]
        if not path:
            logger.error("Folder subscription is not found")
            raise ValueError("Folder subscription is not found")
        path = path[0]
        self.agent.untrack_folder(files)
        self.database.upsert_file_subscription({"subscription_id": None,        #TODO not yet decided
                                                "host_id": self.host_id,
                                                "path": path,
                                                "target_type": "folder",
                                                "status": "removed"})
        del self.track_folders[path]

    def execute_movement(self, file_path, destination_mount, recommendation_id = None):
        """
        Execute file movement
        """
        move_id = str(uuid.uuid4())
        move_handle = self.agent.start_move_file(file_path, destination_mount)
        self.movements[move_id] = move_handle
        record = {"move_id": move_id,
                  "recommendation_id": recommendation_id,
                  "host_id": self.host_id,
                  "source_path": move_handle.source_path,
                  "target_path": move_handle.destination_path,
                  "bytes_total": move_handle.total_bytes,
                  "status": "in_progress",
                  "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                  }
        self.database.save_file_move_record(record)
        return move_id

    def get_action_status(self, action_id):
        action = self.movements[action_id]
        result = action.result()
        if isinstance(result, ErrorCode):
            result = result.name
            logger.error(f"File movement error: {result}")
        return {"progress": action.progress(),
                "is_running": action.is_running(),
                "result": result
                }