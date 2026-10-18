from dataclasses import asdict


def normalize_windows_device(devices) -> list[dict]:
    normalized_device = []
    for device in devices:
        device_dict = asdict(device)
        normalized_device.append(device_dict)
    return normalized_device

def normalize_windows_device_metric(metrics) -> list[dict]:
    normalized_device_metric = []
    for metric in metrics:
        device_metric_dict = asdict(metric)
        normalized_device_metric.append(device_metric_dict)
    return normalized_device_metric

def normalize_windows_process_metric(metrics) -> list[dict]:
    normalized_process_metric = []
    for metric in metrics:
        process_metric_dict = asdict(metric)
        normalized_process_metric.append(process_metric_dict)
    return normalized_process_metric

def normalize_windows_file_activity(activities) -> list[dict]:
    normalized_file_activity = []
    for activity in activities:
        file_activity_dict = asdict(activity)
        normalized_file_activity.append(file_activity_dict)
    return normalized_file_activity

def normalize_windows_collection_health(collection):
    pass

def normalize_linux_device():
    pass

def normalize_linux_device_metric():
    pass

def normalize_linux_process_metric():
    pass

def normalize_linux_file_activity():
    pass