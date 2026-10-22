import json
from datetime import datetime, timezone
from pathlib import Path

from backend.algorithms.common.validation import parse_utc

MOCK_PATH = (Path(__file__).resolve().parents[2] / "tests/fixtures/d2_demo/algo01_input.json")

def time_format_transfer(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def load_demo_input(host_id, *, evaluation_time_utc=None):

    if not isinstance(host_id, str) or not host_id.strip():
        raise ValueError("host_id should have real value")
    
    data = json.loads(MOCK_PATH.read_text(encoding="utf-8"))

    if evaluation_time_utc is None:
        evaluation_time = datetime.now(timezone.utc)
    else:
        evaluation_time = parse_utc(evaluation_time_utc)

    original_time = parse_utc(data['realtime']['evaluation_time_utc'])
    shift = evaluation_time - original_time

    data['realtime']['host_id'] = host_id
    data['realtime']['evaluation_time_utc'] = time_format_transfer(evaluation_time)

    for device in data["devices"]:
        device["host_id"] = host_id

    for activity in data['history']['file_activity']:
        activity['host_id'] = host_id
        activity['source'] = 'mock:d2-demo'

        # Shift mock time to curr time 
        for key in ('window_start_utc', 'window_end_utc'):
            original_timestamp = parse_utc(activity[key])
            activity[key] = time_format_transfer(original_timestamp + shift)

    # Mock capabilities
    data['capabilities'].update({
        'file_access_metrics':True,   ## Just for mock
        'file_move': False,
        'file_level_pooling': False,
        'ssd_caching': False,
        'dry_run_action': False,
        'notes':[
            "demo_mode",
            "simulated_file_activity",
        ],
    })

    return data 
