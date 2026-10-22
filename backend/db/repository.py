import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class SQLiteHistoryRepository:
    def __init__(self, db_path: str = "wsd.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        schema_path = Path(__file__).parent / "schema.sql"
        with self._get_connection() as conn:
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            conn.commit()

    # For Shengrong (Core): Ingests discovered storage devices
    def upsert_devices(self, devices: List[Dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for dev in devices:
                mount_points_str = json.dumps(dev.get("mount_points", []))
                cursor.execute(
                    """
                    INSERT INTO devices (
                        device_id, host_id, display_name, media_type,
                        capacity_bytes, free_bytes, mount_points, is_available, last_seen_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(device_id) DO UPDATE SET
                        display_name = excluded.display_name,
                        media_type = excluded.media_type,
                        capacity_bytes = excluded.capacity_bytes,
                        free_bytes = excluded.free_bytes,
                        mount_points = excluded.mount_points,
                        is_available = excluded.is_available,
                        last_seen_utc = excluded.last_seen_utc
                    """,
                    (
                        dev["device_id"],
                        dev.get("host_id", "default_host"),
                        dev.get("display_name"),
                        dev.get("media_type", "unknown"),
                        dev.get("capacity_bytes"),
                        dev.get("free_bytes"),
                        mount_points_str,
                        1 if dev.get("is_available", True) else 0,
                        now,
                    ),
                )
            conn.commit()

    # For Shengrong (Core): Ingests periodic physical device I/O telemetry
    def ingest_device_metrics(self, samples: List[Dict[str, Any]]) -> None:
        if not samples:
            return
        records = [
            (
                s["device_id"],
                s.get("host_id", "default_host"),
                s["timestamp_utc"],
                s.get("sample_window_seconds", 1.0),
                s.get("read_bytes_per_sec"),
                s.get("write_bytes_per_sec"),
                s.get("read_iops"),
                s.get("write_iops"),
                s.get("avg_read_latency_ms"),
                s.get("avg_write_latency_ms"),
                s.get("source", "os_agent"),
            )
            for s in samples
        ]
        with self._get_connection() as conn:
            conn.cursor().executemany(
                """
                INSERT INTO device_metrics (
                    device_id, host_id, timestamp_utc, sample_window_seconds,
                    read_bytes_per_sec, write_bytes_per_sec, read_iops, write_iops,
                    avg_read_latency_ms, avg_write_latency_ms, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()

    # For Shengrong (Core): Ingests per-process I/O telemetry with stable composite IDs
    def ingest_process_metrics(self, samples: List[Dict[str, Any]]) -> None:
        if not samples:
            return
        records = []
        for s in samples:
            pid = s["pid"]
            start_time = s.get("start_time_utc", "")
            process_instance_id = s.get("process_instance_id") or f"{pid}_{start_time}"
            records.append((
                process_instance_id,
                s.get("host_id", "default_host"),
                pid,
                start_time,
                s.get("process_name"),
                s["timestamp_utc"],
                s.get("sample_window_seconds", 1.0),
                s.get("read_bytes_per_sec"),
                s.get("write_bytes_per_sec"),
                s.get("attributed_device_id"),
            ))
        with self._get_connection() as conn:
            conn.cursor().executemany(
                """
                INSERT INTO process_metrics (
                    process_instance_id, host_id, pid, start_time_utc,
                    process_name, timestamp_utc, sample_window_seconds,
                    read_bytes_per_sec, write_bytes_per_sec, attributed_device_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()
    
    # For Shengrong (Core): Safe no-op ingestion for file activity ---
    def ingest_file_activity(self, samples: List[Dict[str, Any]]) -> None:
        """
        Ingests file-level activity if provided by OS agent.
        Currently safely accepts incoming samples without error while file heat 
        tracking is uninstrumented at the OS level.
        """
        # Kept as safe no-op so Core's ingestion loop does not raise AttributeError
        pass

    # For John & Jesslyn (Algorithm) & Shengrong (HTTP-01f): Device historical range and aggregation
    def query_device_history(
        self,
        device_ids: List[str],
        start_utc: str,
        end_utc: str,
        bucket_seconds: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not device_ids:
            return []

        placeholders = ",".join("?" for _ in device_ids)
        params: List[Any] = list(device_ids) + [start_utc, end_utc]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if not bucket_seconds or bucket_seconds <= 0:
                # Raw records
                query = f"""
                    SELECT device_id, timestamp_utc, read_bytes_per_sec, write_bytes_per_sec,
                           read_iops, write_iops, avg_read_latency_ms, avg_write_latency_ms
                    FROM device_metrics
                    WHERE device_id IN ({placeholders})
                      AND timestamp_utc BETWEEN ? AND ?
                    ORDER BY timestamp_utc ASC
                """
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

            # Aggregated by bucket window
            # strftime('%s', timestamp_utc) turns ISO timestamps into epoch seconds in SQLite
            query = f"""
                SELECT 
                    device_id,
                    strftime('%Y-%m-%dT%H:%M:%SZ', (strftime('%s', timestamp_utc) / ?) * ?, 'unixepoch') AS timestamp_utc,
                    COUNT(*) as sample_count,
                    AVG(read_bytes_per_sec) as avg_read_bytes_per_sec,
                    AVG(write_bytes_per_sec) as avg_write_bytes_per_sec,
                    AVG(read_iops) as avg_read_iops,
                    AVG(write_iops) as avg_write_iops,
                    AVG(avg_read_latency_ms) as avg_read_latency_ms,
                    AVG(avg_write_latency_ms) as avg_write_latency_ms
                FROM device_metrics
                WHERE device_id IN ({placeholders})
                  AND timestamp_utc BETWEEN ? AND ?
                GROUP BY device_id, (strftime('%s', timestamp_utc) / ?)
                ORDER BY timestamp_utc ASC
            """
            agg_params = [bucket_seconds, bucket_seconds] + params + [bucket_seconds]
            cursor.execute(query, agg_params)
            return [dict(row) for row in cursor.fetchall()]

    # For Shengrong (HTTP-01m) & Danny (UI): Historical I/O for specific app instances (US-02)
    def query_process_history(
        self,
        process_instance_ids: List[str],
        start_utc: str,
        end_utc: str,
        bucket_seconds: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not process_instance_ids:
            return []

        placeholders = ",".join("?" for _ in process_instance_ids)
        params: List[Any] = list(process_instance_ids) + [start_utc, end_utc]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if not bucket_seconds or bucket_seconds <= 0:
                query = f"""
                    SELECT process_instance_id, pid, process_name, timestamp_utc, 
                    sample_window_seconds, read_bytes_per_sec, write_bytes_per_sec, 
                    attributed_device_id
                    FROM process_metrics
                    WHERE process_instance_id IN ({placeholders})
                    AND timestamp_utc BETWEEN ? AND ?
                    ORDER BY timestamp_utc ASC
                """
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            # Aggregated by bucket window
            query = f"""
                SELECT 
                    process_instance_id,
                    pid,
                    process_name,
                    strftime('%Y-%m-%dT%H:%M:%SZ', (strftime('%s', timestamp_utc) / ?) * ?, 'unixepoch') AS timestamp_utc,
                    COUNT(*) as sample_count,
                    AVG(read_bytes_per_sec) as avg_read_bytes_per_sec,
                    AVG(write_bytes_per_sec) as avg_write_bytes_per_sec,
                    attributed_device_id
                FROM process_metrics
                WHERE process_instance_id IN ({placeholders})
                  AND timestamp_utc BETWEEN ? AND ?
                GROUP BY process_instance_id, (strftime('%s', timestamp_utc) / ?)
                ORDER BY timestamp_utc ASC
            """
            agg_params = [bucket_seconds, bucket_seconds] + params + [bucket_seconds]
            cursor.execute(query, agg_params)
            return [dict(row) for row in cursor.fetchall()]

    # For John & Jesslyn (Algorithm): Returns empty list when OS agents lack file telemetry
    def query_file_heat(
        self,
        start_utc: str,
        end_utc: str,
        limit: int = 100,
        device_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        # Returns empty list as file-level tracking is currently unsupported from OS agents
        return []

    #SETTINGS & RECOMMENDATIONS

    # For Shengrong (HTTP-01i) & Danny (UI): Persist user preferences & auto-mode flags, this was for US-06
    # but I chose to get it done anyway since it's part of the repo 
    def save_settings(self, settings: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for key, val in settings.items():
                val_str = json.dumps(val) if not isinstance(val, str) else val
                cursor.execute(
                    """
                    INSERT INTO app_settings (key, value, updated_at_utc)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at_utc = excluded.updated_at_utc
                    """,
                    (key, val_str, now),
                )
            conn.commit()

    # For Shengrong (HTTP-01i) & John/Jesslyn (ALGO): Retrieve current active settings
    def get_settings(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM app_settings")
            result = {}
            for row in cursor.fetchall():
                try:
                    result[row["key"]] = json.loads(row["value"])
                except (json.JSONDecodeError, TypeError):
                    result[row["key"]] = row["value"]
            return result

    # For John & Jesslyn (Algorithm): Store generated recommendations
    def save_recommendations(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        records = [
            (
                r["recommendation_id"],
                r["mode"],
                r["action"],
                r.get("file_id"),
                r.get("source_device_id"),
                r.get("target_device_id"),
                r["reason"],
                r["created_at_utc"],
                1 if r.get("requires_approval", True) else 0,
                json.dumps(r.get("estimated_benefit")),
                json.dumps(r.get("constraints", [])),
            )
            for r in items
        ]
        with self._get_connection() as conn:
            conn.cursor().executemany(
                """
                INSERT INTO recommendations (
                    recommendation_id, mode, action, file_id, source_device_id,
                    target_device_id, reason, created_at_utc, requires_approval,
                    estimated_benefit, constraints
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(recommendation_id) DO UPDATE SET
                    mode = excluded.mode,
                    action = excluded.action,
                    reason = excluded.reason,
                    created_at_utc = excluded.created_at_utc,
                    requires_approval = excluded.requires_approval,
                    estimated_benefit = excluded.estimated_benefit,
                    constraints = excluded.constraints
                """,
                records,
            )
            conn.commit()

    # For Shengrong (HTTP-01g) & Danny (UI): Surface recommendations to the user
    def list_recommendations(self, mode: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if mode:
                cursor.execute("SELECT * FROM recommendations WHERE mode = ? ORDER BY created_at_utc DESC", (mode,))
            else:
                cursor.execute("SELECT * FROM recommendations ORDER BY created_at_utc DESC")

            rows = cursor.fetchall()
            output = []
            for row in rows:
                item = dict(row)
                item["requires_approval"] = bool(item["requires_approval"])
                if item.get("estimated_benefit"):
                    item["estimated_benefit"] = json.loads(item["estimated_benefit"])
                if item.get("constraints"):
                    item["constraints"] = json.loads(item["constraints"])
                output.append(item)
            return output