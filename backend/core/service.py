# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from datetime import datetime, timezone
from .demo_data import load_demo_input
import logging
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

    def start(self)-> None:
        if not self.demo_mode:
            self.agent.start()

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

            file_activity = self.agent.get_file_activity(60)

            # Generate evaluation time AFTER collecting file activity
            evaluation_time_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            realtime = {
                "host_id": host_id,
                "evaluation_time_utc": evaluation_time_utc
            }

            history={"file_activity": file_activity}
            mode_config= {} #Not required in D2
            capabilities = self.capabilities or {} #TODO agent not done

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