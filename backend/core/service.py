from datetime import datetime, timezone

class CoreService:
    def __init__(self, agent, algorithm, database):
        self.agent = agent
        self.algorithm = algorithm
        self.database = database

    def start(self) -> None:
        self.agent.start()

    def close(self) -> None:
        self.agent.close()

    def collect_and_record(self):
        """
        Collect one snapshot of device and process I/O data and persist it to database.

        flow: Agent -> CORE -> DB
        """
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
        return self.agent.get_devices()

    def get_current_device_metrics(self):
        return self.agent.get_device_metrics()

    def get_recommendations(self, mode=None):
        return self.database.list_recommendations(mode)

    def get_current_process_activity(self):
        """
        Return current per-process I/O activity.

        Flow: Agent -> CORE -> HTTP/UI
        User Story: US-01
        """
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
        capabilities= {} #TODO agent not done
        recommendations =self.algorithm.evaluate_raid0(devices, realtime, history, mode_config, capabilities)
        self.database.save_recommendations(recommendations)
        return recommendations



