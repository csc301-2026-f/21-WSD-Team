"""D4 SSD caching ML predictor"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
from sklearn.feature_selection import VarianceThreshold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline

HDD_AVG_READ_MS = 8.5
SSD_AVG_READ_MS = 0.15
BYTES_PER_MIB = 1024.0 * 1024.0
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "cache_model_results" / "cache_logreg_model.joblib"


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def extract_features(
    read_rate: float,
    read_ops: int,
    write_ops: int,
    read_bytes: int,
    size_bytes: int,
    historical_read_rate: float | None = None,
) -> list[float]:
    """Features (all normalized to [0, 1] scale):
    
    x0: Bias (1.0)
    x1: Normalized log read rate -> log1p(read_rate) / 5.0
    x2: Read-only purity -> read_ops / (read_ops + write_ops)
    x3: Compactness score -> 1.0 / (1.0 + log1p(size_mib))
    x4: Random-read affinity -> 1.0 - min(1.0, avg_read_size_bytes / 1_048_576)
    x5: Temporal burst ratio -> min(2.0, recent_rate / baseline_rate) / 2.0
    """
    # Normalized log read rate
    norm_log_rate = min(1.5, math.log1p(max(0.0, read_rate)) / 5.0)

    # Read-only purity
    total_ops = max(1, read_ops + write_ops)
    read_purity = read_ops / total_ops

    # Compactness score
    size_mib = max(1e-6, size_bytes / BYTES_PER_MIB)
    compactness = 1.0 / (1.0 + math.log1p(size_mib))

    # Random-read affinity
    avg_read_size_bytes = (read_bytes / read_ops) if read_ops > 0 else float(size_bytes)
    random_affinity = 1.0 - min(1.0, avg_read_size_bytes / BYTES_PER_MIB)

    # Temporal burst ratio
    if historical_read_rate and historical_read_rate > 0:
        burst_ratio = min(2.0, read_rate / historical_read_rate) / 2.0
    else:
        burst_ratio = 0.5

    return [
        norm_log_rate,
        read_purity,
        compactness,
        random_affinity,
        burst_ratio
    ]


def build_sliding_window_dataset(
    activity_rows: Iterable[dict],
    horizon_minutes: int = 10,
    min_future_reads: int = 15,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[datetime]]:
    """Build a sliding-window dataset, (X, y, groups, label_end_times)"""
    by_file: dict[str, list[dict]] = {}
    for row in activity_rows:
        if isinstance(row, dict) and isinstance(row.get("file_id"), str):
            by_file.setdefault(row["file_id"], []).append(row)

    X, y, groups, label_end_times = [], [], [], []
    horizon = timedelta(minutes=horizon_minutes)

    for fid, rows in by_file.items():
        rows_sorted = sorted(rows, key=lambda r: str(r.get("window_end_utc", "")))
        parsed = []
        for r in rows_sorted:
            try:
                t_start = _parse_ts(r["window_start_utc"])
                t_end = _parse_ts(r["window_end_utc"])
                parsed.append((t_start, t_end, r))
            except (KeyError, ValueError, TypeError):
                continue

        ewma_rate = 0.0
        for i, (t_start, t_end, curr_r) in enumerate(parsed):
            dur_s = max(1.0, (t_end - t_start). total_seconds())
            c_reads = max(0, int(curr_r.get("read_ops")) or 0)
            c_writes = max(0, int(curr_r.get("write_ops")) or 0)
            c_bytes = max(0, int(curr_r.get("read_bytes")) or 0)
            c_size = max(1, int(curr_r.get("file_size_bytes")) or 0)
            c_rate = c_reads / dur_s

            ewma_rate = c_rate if i == 0 else (0.4 * c_rate + 0.6 * ewma_rate)

            target_end = t_end + horizon
            future_rows = [
                nxt_r for (_, nxt_end, nxt_r) in parsed[i + 1 :] 
                if t_end < nxt_end <= target_end
            ]
            if not future_rows:
                continue

            f_reads = sum(max(0, int(f_r.get("read_ops")) or 0) for f_r in future_rows)
            f_writes = sum(max(0, int(f_r.get("write_ops")) or 0) for f_r in future_rows)
            label = 1 if (f_reads >= min_future_reads and f_writes == 0) else 0

            X.append(
                extract_features(
                    read_rate=c_rate,
                    read_ops=c_reads,
                    write_ops=c_writes,
                    read_bytes=c_bytes,
                    size_bytes=c_size,
                    historical_read_rate=ewma_rate
                )
            )
            y.append(label)
            groups.append(fid)
            label_end_times.append(max(_parse_ts(f_r["window_end_utc"] for f_r in future_rows)))

    if not X:
        return np.empty((0, 5)), np.empty((0,), dtype=int), np.empty((0,)), []

    return np.array(X, dtype=float), np.array(y, dtype=int), np.array(groups, dtype=object), label_end_times


def train_and_val_model(
    activity_rows: Iterable[dict],
    train_ratio: float = 0.75,
    model_path: Path = DEFAULT_MODEL_PATH
) -> dict:
    """Chronologically split history for both training and validation datasets,
    tune Pipeline(VarianceThreshold + LogisticRegression) via StratifiedGroupKFold,
    evaluate held-out validation accuracy and f1-score, and save model via joblib.
    """
    X, y, groups, label_end_times = build_sliding_window_dataset(activity_rows)
    if len(X) < 10 or len(np.unique(y)) < 2:
        raise ValueError("Insufficient data in sliding window dataset for training")

    order = np.argsort(label_end_times)
    X, y, groups = X[order], y[order], groups[order]
    label_end_times = [label_end_times[i] for i in order]

    split_idx = int(len(y) * train_ratio)
    cutoff_time = label_end_times[split_idx]
    train_mask = np.array([t < cutoff_time for t in label_end_times])
    val_mask = ~train_mask
    X_train, y_train, groups_train = X[train_mask], y[train_mask], groups[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]

    pipe = Pipeline([
        ("var_thresh", VarianceThreshold(threshold=0.0)),
        ("clf", LogisticRegression(max_iter=500, class_weight="balanced", random_state=42))
    ])

    n_unique_groups = len(np.unique(groups_train))
    n_splits = min(3, n_unique_groups)
    if n_splits >= 2 and np.min(np.bincount(y_train)) >= 2:
        cv = StratifiedGroupKFold(n_splits=n_splits)
        grid_search = GridSearchCV(
            pipe, 
            param_grid={
                "clf__C": [0.1, 1.0, 10.0]
            }, 
            cv=cv, 
            scoring="f1" 
        )
        grid_search.fit(X_train, y_train, groups=groups)
        best_model = grid_search.best_estimator_
    else:
        best_model = pipe.fit(X_train, y_train)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, model_path)

    metrics = {
        "train_samples": int(len(y_train)), 
        "val_samples": int(len(y_val))
    }

    if len(y_val) > 0:
        y_pred = best_model.predict(X_val)
        metrics["val_accuracy"] = round(float(accuracy_score(y_val, y_pred)), 4)
        metrics["val_f1"] = round(float(f1_score(y_val, y_pred, zero_division=0)), 4)
        metrics["report"] = classification_report(y_val, y_pred, zero_division=0)
    return metrics


def _build_start_pipeline() -> Pipeline:
    """Build starting pipeline when when no trained .joblib exists yet"""
    pipe = Pipeline([
        ("var_thresh", VarianceThreshold(threshold=0.0)),
        ("clf", LogisticRegression()),
    ])
    X_anchor = np.array([
        [0.85, 1.00, 0.80, 0.90, 0.85],  # Hot, read-only, small, random -> cache (1)
        [0.70, 0.95, 0.65, 0.75, 0.70],  # Warm, read-mostly, compact -> cache (1)
        [0.20, 0.30, 0.15, 0.10, 0.25],  # Cold, write-heavy, huge, sequential -> skip (0)
        [0.60, 0.40, 0.20, 0.20, 0.40],  # Frequent writes invalidating cache -> skip (0)
    ])
    y_anchor = np.array([1, 1, 0, 0])
    pipe.fit(X_anchor, y_anchor)
    return pipe


def load_cache_model(model_path: Path = DEFAULT_MODEL_PATH) -> Pipeline:
    """Load .joblib Pipeline if it exists, otherwise return starting pipeline"""
    if model_path.exists():
        return joblib.load(model_path)
    return _build_start_pipeline()


def score_cache_candidates(
    candidates: list[dict],
    activity_rows: list[dict],
    model_path: Path = DEFAULT_MODEL_PATH,
    horizon_seconds: float = 600.0,
) -> list[dict]:
    """Score candidate files using Pipeline and rank by value density."""
    if not candidates:
        return []
    model = load_cache_model(model_path)

    by_file: dict[str, list[dict]] = {}
    for row in activity_rows:
        if isinstance(row, dict) and isinstance(row.get("file_id"), str):
            by_file.setdefault(row["file_id"], []).append(row)

    ewma_by_file: dict[str, list[dict]] = {}
    for fid, rows in by_file.items():
        rows_sorted = sorted(rows, key=lambda r: str(r.get("window_end_utc", "")))
        ewma = 0.0
        for idx, r in enumerate(rows_sorted):
            rate = max(0, int(r.get("read_ops") or 0)) / 60.0
            ewma = rate if idx == 0 else (0.4 * rate + 0.6 * ewma)
        ewma_by_file[fid] = ewma

    X_cand = np.array(
        [
            extract_features(
                read_rate=row["read_rate"],
                read_ops=row["read_ops"],
                write_ops=row.get("write_ops", 0),
                read_bytes=row.get("read_bytes", row["size"]),
                size_bytes=row["size"],
                historical_read_rate=ewma_by_file.get(row["file_id"]),
            )
            for row in candidates
        ],
        dtype=float,
    )

    prob = model.predict_proba(X_cand)[:, 1]
    latency_gain_ms = max(0.1, HDD_AVG_READ_MS - SSD_AVG_READ_MS)
    enriched: list[dict] = []

    for row, prob in zip(candidates, prob):
        fid = row["file_id"]
        base_rate = ewma_by_file.get(fid)
        effective_rate = (
            0.6 * row["read_rate"] + 0.4 * base_rate
            if base_rate is not None
            else row["read_rate"]
        )
        predicted_reads = effective_rate * horizon_seconds * prob
        estimated_benefit_ms = round(predicted_reads * latency_gain_ms, 2)
        size_mib = max(1e-3, row["size"] / BYTES_PER_MIB)
        value_density = estimated_benefit_ms / size_mib

        enriched.append({
            **row,
            "ml_cache_prob": round(float(prob, 4)),
            "predicted_future_reads": round(predicted_reads, 2),
            "estimated_benefit_ms": estimated_benefit_ms,
            "cache_value_density": round(value_density, 4),
        })

    return sorted(
        enriched,
        key=lambda r: (-r["cache_value_density"], -r["ml_cache_prob"], r["size"], r["file_id"]),
    )