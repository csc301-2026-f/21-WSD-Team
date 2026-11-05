# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only


class DataBaseAdaptor:
    def __init__(self, repository):
        self.repository = repository
    def upsert_devices(self, devices: list[dict]) -> None:
        return self.repository.upsert_devices(devices)

    def ingest_device_metrics(self, samples: list[dict]) -> None:
        return self.repository.ingest_device_metrics(samples)

    def ingest_process_metrics(self, samples: list[dict]) -> None:
        return self.repository.ingest_process_metrics(samples)

    def ingest_file_activity(self, samples: list[dict]) -> None:
        return self.repository.ingest_file_activity(samples)

    def query_device_history(self, device_ids: list[str], start_utc: str,
                             end_utc: str, bucket_seconds: int | None = None) -> list[dict]:
        return self.repository.query_device_history(device_ids, start_utc, end_utc, bucket_seconds)

    def query_process_history(self, process_instance_ids: list[str], start_utc: str,
                              end_utc: str, bucket_seconds: int | None = None) -> list[dict]:
        return self.repository.query_process_history(process_instance_ids, start_utc, end_utc, bucket_seconds)

    def query_file_heat(self, start_utc: str, end_utc: str, limit: int = 100,
                        device_ids: list[str] | None = None) -> list[dict]: # CONDITIONAL
        return self.repository.query_file_heat(start_utc, end_utc, limit, device_ids)

    def get_settings(self) -> dict:
        return self.repository.get_settings()

    def save_settings(self, settings: dict) -> None:
        return self.repository.save_settings(settings)

    def save_recommendations(self, items: list[dict]) -> None:
        return self.repository.save_recommendations(items)

    def list_recommendations(self, mode: str | None = None) -> list[dict]:
        return self.repository.list_recommendations(mode)
