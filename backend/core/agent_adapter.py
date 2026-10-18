from .normalization import (normalize_windows_device,
                            normalize_windows_device_metric,
                            normalize_windows_process_metric,
                            normalize_windows_file_activity)

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
        pass

    def get_devices(self, drive_name):
        pass

    def get_device_metrics(self, drive_name):
        pass

    def get_process_metrics(self):
        pass

    def get_file_activity(self):
        pass

    def close(self):
        pass