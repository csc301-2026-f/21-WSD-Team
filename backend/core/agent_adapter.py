from .normalization import (normalize_windows_device,
                            normalize_windows_device_metric,
                            normalize_windows_process_metric,
                            normalize_windows_file_activity,
                            normalize_linux_device,
                            normalize_linux_device_metric,
                            normalize_linux_process_metric,
                            normalize_linux_file_activity)

class WindowsAgentAdapter:
    def __init__(self, backend):
        self.backend = backend

    def start(self) -> None:
        self.backend.start()

    def get_devices(self) -> list[dict]:
        return normalize_windows_device(self.backend.get_devices())

    def get_device_metrics(self, sample_window_seconds = 10.0) -> list[dict]:
        return normalize_windows_device_metric(self.backend.get_device_metrics(sample_window_seconds))

    def get_process_metrics(self, sample_window_seconds = 10.0) -> list[dict]:
        return normalize_windows_process_metric(self.backend.get_process_metrics(sample_window_seconds))

    def get_file_activity(self, window_start_ns, window_end_ns) -> list[dict]:
        return normalize_windows_file_activity(self.backend.get_file_activity(window_start_ns, window_end_ns))

    def close(self):
        self.backend.close()


class LinuxAgentAdapter:
    def __init__(self, backend):
        self.backend = backend

    def start(self) -> None:
        self.backend.start()

    def get_devices(self) -> list[dict]:
        return normalize_linux_device(self.backend.list_devices(), self.backend.host_id)

    def get_device_metrics(self, sample_window_seconds = 10.0) -> list[dict]:
        devices = self.backend.list_devices()
        device_metric = []
        for device in devices:
            device_id = device.device_id
            metric = self.backend.get_device_io(sample_window_seconds, device_id)
            if metric is not None:
                device_metric.append((device_id, metric))
        return normalize_linux_device_metric(device_metric, self.backend.host_id)

    def get_process_metrics(self, sample_window_seconds = 10.0) -> list[dict]:
        pass
    #TODO agent not done

    def get_file_activity(self):
        pass
    #TODO agent not done

    def close(self):
        self.backend.close()