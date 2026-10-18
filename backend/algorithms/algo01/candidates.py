"""Select the latest usable FileActivity window; never sum overlapping history."""
from collections import defaultdict
from ..common.validation import is_integer, is_text, is_fresh, parse_utc, is_mock_source


def _read_window(row, context, warnings):
    """Check combined CORE input, not the OS collector's original completeness."""
    if not isinstance(row, dict):
        warnings.add("invalid_file_activity")
        return None
    if not (is_text(row.get("file_id")) and is_text(row.get("device_id"))
            and is_integer(row.get("file_size_bytes"), 1) and is_text(row.get("source"))
            and row.get("host_id") == context.host):
        warnings.add("incomplete_file_activity")
        return None
    if row.get("path") is not None and not is_text(row["path"]):
        warnings.add("invalid_file_path")
        return None
    if not (is_integer(row.get("read_ops")) and is_integer(row.get("write_ops"))):
        warnings.add("missing_read_or_write_ops")
        return None
    try:
        start, end = parse_utc(row.get("window_start_utc")), parse_utc(row.get("window_end_utc"))
        duration = (end - start).total_seconds()
    except (ValueError, TypeError, OverflowError):
        warnings.add("invalid_or_stale_activity_window")
        return None
    if not (context.config["min_window_seconds"] <= duration <= context.config["max_window_seconds"]
            and is_fresh(row.get("window_end_utc"), context.now, context.config["max_age_seconds"])):
        warnings.add("invalid_or_stale_activity_window")
        return None
    return {"row": row, "start": start, "end": end, "duration": duration}


def _choose_latest(windows, warnings):
    """Collapse equivalent newest windows; conflicting newest values stay ambiguous."""
    newest = max(window["end"] for window in windows)
    unique = {}
    for window in windows:
        if window["end"] != newest:
            continue
        row = window["row"]
        key = (window["start"], row["device_id"], row["file_size_bytes"],
               row["read_ops"], row["write_ops"], row["source"])
        unique[key] = window
    if len(unique) != 1:
        warnings.add("conflicting_latest_file_activity")
        return None
    return next(iter(unique.values()))


def collect_candidates(context, devices, warnings):
    """Choose one recent window/file, then rank qualifying HDD files by read rate."""
    by_file = defaultdict(list)
    for row in context.activity:
        window = _read_window(row, context, warnings)
        if window is not None:
            by_file[row["file_id"]].append(window)
    result = []
    for file_id in sorted(by_file):
        window = _choose_latest(by_file[file_id], warnings)
        if window is None:
            continue
        row = window["row"]
        # read times / (read times + write times) >= 80%
        source, reads, writes = row["device_id"], row["read_ops"], row["write_ops"]
        device = devices.get(source)
        if not device or device.get("is_available") is not True:
            warnings.add("source_unavailable_or_unknown")
            continue
        if device.get("media_type") != "hdd":
            warnings.add("source_outside_d2_hdd_scope")
            continue
        rate = reads / window["duration"]
        if reads == 0 or rate < context.config["min_read_ops_per_sec"]:
            warnings.add("insufficient_read_activity")
            continue
        if reads / (reads + writes) < context.config["min_read_fraction"]:
            warnings.add("write_heavy_workload_deferred")
            continue
        result.append({"file_id": file_id, "source": source, "size": row["file_size_bytes"],
            "read_rate": rate, "read_ops": reads, "is_mock": is_mock_source(row["source"])})
    # Tie breaker, choose highest freq; if tie, smaller size file wins; if tie, smaller id wins
    return sorted(result, key=lambda row: (-row["read_rate"], row["size"], row["file_id"]))
