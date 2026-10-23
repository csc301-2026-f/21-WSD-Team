from .contracts import (
    Device,
    DeviceMetric,
    ProcessMetric,
    FileActivity,
    CollectionHealth,
)
from .device_provider import DeviceProvider
from .etw_source import EtwSource
from .aggregation import EventAggregator


class WindowsBackend:
    def __init__(
        self,
        host_id: str,
        etw_source: EtwSource,
        device_provider: DeviceProvider,
    ):
        self.host_id = host_id
        self.etw_source = etw_source
        self.device_provider = device_provider
        self.aggregator = EventAggregator(host_id)
        self._started = False

    def start(self) -> None:
        if self._started:
            return

        self.etw_source.start(self.aggregator.add_event)
        self._started = True

    def get_devices(self) -> list[Device]:
        return self.device_provider.list_devices()

    def get_device_metrics(
        self,
        sample_window_seconds: float = 10.0,
    ) -> list[DeviceMetric]:
        devices = self.get_devices()

        return self.aggregator.device_metrics(
            device_ids=[d.device_id for d in devices],
            sample_window_seconds=sample_window_seconds,
        )

    def get_process_metrics(
        self,
        sample_window_seconds: float = 10.0,
    ) -> list[ProcessMetric]:
        return self.aggregator.process_metrics(
            sample_window_seconds=sample_window_seconds,
        )

    def get_file_activity(
        self,
        sample_window_seconds: int,
        now_ns: int | None = None,
    ) -> list[FileActivity]:
        """Return verified file-level activity, if available."""
        return self.aggregator.file_activity(
            sample_window_seconds=sample_window_seconds,
            now_ns=now_ns,
        )

    def get_collection_health(self) -> CollectionHealth: 
        return self.etw_source.get_health() #implementation may get changed

    def close(self) -> None:
        if self._started:
            self.etw_source.stop()
            self._started = False
