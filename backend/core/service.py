# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from datetime import datetime, timezone
from .demo_data import load_demo_input

class CoreService:
    def __init__(self, agent, algorithm, database, capabilities=None, demo_mode = False, host_id = None):
        self.agent = agent
        self.algorithm = algorithm
        self.database = database
        self.capabilities = capabilities
        self.demo_mode = demo_mode
        self.host_id = host_id

    def start(self)-> None:
        if not self.demo_mode:
            self.agent.start()

    def close(self) -> None:
        if not self.demo_mode:
            self.agent.close()

    def collect_and_record(self):
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
            evaluation_time_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            realtime={
                "host_id": host_id,
                "evaluation_time_utc": evaluation_time_utc}
            file_activity = None #TODO agent not done
            history={"file_activity": file_activity}
            mode_config= {} #Not required in D2
            capabilities = self.capabilities or {} #TODO agent not done
        recommendations =self.algorithm.evaluate_raid0(devices, realtime, history, mode_config, capabilities)
        self.database.save_recommendations(recommendations)
        return recommendations



