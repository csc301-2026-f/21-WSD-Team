from dataclasses import dataclass
from datetime import datetime
from ..common.validation import is_integer, is_number, is_text, parse_utc

# For D4 ML Implementation
GOAL_PROB_THRESHOLDS = {
    "performance": 0.45,
    "balanced": 0.60,
    "lifespan": 0.75,
}

DEFAULTS = {
    "goal": "performance", 
    "min_read_ops_per_sec": 0.1, 
    "min_read_fraction": 0.8,
    "min_window_seconds": 60, 
    "max_window_seconds": 3600, 
    "max_age_seconds": 300,
    "reserve_bytes": 1073741824, 
    "reserve_fraction": 0.1, 
    "max_recommendations": 10,
    # For D4 ML Implementation
    "min_cache_prob": None
}

class PolicyInputError(ValueError):
    def __init__(self, code, timestamp=None):
        super().__init__(code)
        self.code, self.timestamp = code, timestamp

@dataclass(frozen=True)
class D2Inputs:
    now: datetime
    timestamp: str
    host: str
    config: dict
    activity: list

def validate_inputs(devices, realtime, history, mode_config, capabilities):
    """Validate the five arguments; never synthesize an evaluation timestamp."""
    try:
        now = parse_utc(realtime.get("evaluation_time_utc") if isinstance(realtime, dict) else None)
    except (ValueError, TypeError, OverflowError):
        raise PolicyInputError("invalid_evaluation_time") from None
    
    timestamp = now.isoformat().replace("+00:00", "Z")

    def reject(code):
        raise PolicyInputError(code, timestamp)
    
    if not (isinstance(devices, list) and isinstance(history, dict) and isinstance(capabilities, dict)):
        reject("invalid_input")

    if not is_text(realtime.get("host_id")):
        reject("missing_host_id")

    if not isinstance(mode_config, dict) or set(mode_config) - set(DEFAULTS):
        reject("invalid_config")

    config = {**DEFAULTS, **mode_config}

    # For D4 ML Implementation
    if config["goal"] not in GOAL_PROB_THRESHOLDS:
        reject("invalid_goal")

    if config["min_cache_prob"] is None:
        config["min_cache_prob"] = GOAL_PROB_THRESHOLDS[config["goal"]]
    elif not is_number(config["min_cache_prob"]) or not (0.0 <= config["min_cache_prob"] <= 1.0):
        reject("invalid_config")

    for key, value in config.items():
        if key == "goal":
            continue

        valid = is_integer(value, 1 if key == "max_recommendations" else 0) if key in (
            "reserve_bytes", "max_recommendations") else is_number(value)
        
        if not valid:
            reject("invalid_config")

    if not (0 <= config["reserve_fraction"] < 1 and 0 <= config["min_read_fraction"] <= 1
            and 0 < config["min_window_seconds"] <= config["max_window_seconds"]):
        reject("invalid_config")

    if capabilities.get("file_access_metrics") is not True:
        reject("unsupported_capability")

    activity = history.get("file_activity", [])

    if not isinstance(activity, list):
        reject("invalid_file_activity_collection")

    return D2Inputs(now, timestamp, realtime["host_id"], config, activity)
