"""D2 capacity totals from the existing Device fields; no disk operations."""
import math
from .validation import is_integer, is_text


def index_devices(devices, host, warnings):
    """Return same-host records, rejecting duplicate device IDs."""
    result = {}
    seen = set()
    for row in devices:
        if not isinstance(row, dict) or not is_text(row.get("device_id")):
            warnings.add("invalid_device_metadata")
            continue
        key = row["device_id"]
        if key in seen:
            raise ValueError("duplicate_device_id")
        seen.add(key)
        if row.get("host_id") == host:
            result[key] = row
    return result


def build_ssd_budgets(devices, reserve_bytes, reserve_fraction):
    """Compute free space minus reserve, keyed by the shared device ID."""
    budgets = {}
    for key, row in devices.items():
        capacity, free = row.get("capacity_bytes"), row.get("free_bytes")
        if (row.get("media_type") == "ssd" and row.get("is_available") is True
                and is_integer(capacity, 1) and is_integer(free) and free <= capacity):
            reserve = max(reserve_bytes, math.ceil(capacity * reserve_fraction))
            budgets[key] = max(0, free - reserve)
    return budgets
