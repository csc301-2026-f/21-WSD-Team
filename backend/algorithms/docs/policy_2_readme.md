# ALGO-02: ML-Assisted SSD Caching (D4 updated)

ALGO-02 recommends caching read-heavy files from HDDs on an SSD. Thanks to the implementation of ML through a logistic-regression model, it uses recent file activity to identify candidates, prioritizing read-value density, scores their likelihood of remaining useful, and fits recommendations within available SSD capacity. 

## How it works

### File filtering

The policy validates the evaluation timestamp, host, configuration, storage devices, and file activity. It considers each file's latest usable activity window when the source device is available HDD storage. By default, a candidate must have at least 0.1 reads per second and at least 80% of its operations must be reads. Stale, malformed, ambiguous, write-heavy, unavailable, and non-HDD records are excluded with warning reasons.

### Cache prediction (D4)

The predictor uses an sklearn pipeline with variance thresholds and logistic regression. Its features are normalized read rate, read-only purity, file compactness, average read-size affinity, and recent read-rate bursts. It estimates the probability that a file will continue to have useful read activity.

For supervised training, `build_sliding_window_dataset` uses one activity window as the input and the following ten minutes as the label window. The label is positive when those ten minutes contain at least 15 reads and no writes. Samples are only built when the full future horizon is present as contiguous, non-overlapping observations; duplicate conflicting windows are discarded.

`train_val_test_model` sorts samples by the end of their label windows and makes the training, validation and test partition ratios 70:15:15 by default. Validation selects the logistic-regression `C` value from 0.1, 1.0, and 10.0 using F1. The final model is fit on training plus validation data, then evaluated once on the held-out test partition. The function returns sample counts, validation/test accuracy, F1-score, and a test classification report, and saves the fitted model to a Joblib file. A split requires enough samples for all three partitions and both classes in training.

The policy's recommendation path loads the saved model when one exists. If there is no saved model, it creates a cold-start pipeline as a fallback so the recommendation path can run.

### Benefit estimate and candidate selection

The model probability gates candidates using `min_cache_prob`. The default thresholds are 0.45 for `performance`, 0.60 for `balanced`, and 0.75 for `lifespan`. The lifespan goal also skips files with writes in the selected activity window. For each surviving candidate, the algorithm estimates future reads over ten minutes and multiplies them by an assumed HDD-to-SSD average read-latency difference (8.5 ms versus 0.15 ms). This value is a ranking estimate, not a measured speedup.

The default selector sorts by recent read rate per byte, then read rate, smaller size, and file ID. It selects files that fit the chosen SSD's usable capacity and the recommendation limit. The selected SSD is the eligible target with the greatest usable budget after reserves.

## Developer Guide

### Setup and examples

Use Python 3.10 or later and install the project dependencies. The algorithm requires NumPy, scikit-learn, and Joblib; pytest is needed to run its tests. From the repository root, run the mock example:

```bash
python -B -m backend.algorithms.algo02.demo --mock-input backend/algorithms/algo02/tests/fixtures/d3-ssd-valid.json
```

The demo accepts only mock-labelled activity and prints `storage_actions_executed: false` to make clear that no cache action is performed.

Run ALGO-02's unit tests with:

```bash
python -B -m pytest backend/algorithms/algo02/tests -q
```

### Train and evaluate with historical activity

Training is a separate operation; `evaluate_ssd_caching_policy` does not train a model during recommendation generation. Once real activity history contains complete input and future-label windows, call the training function from a script or Python session:

```python
from backend.algorithms.algo02.prediction import train_val_test_model

metrics = train_val_test_model(file_activity_rows)
print(metrics)
```

`file_activity_rows` must contain timestamped records with `file_id`, `window_start_utc`, `window_end_utc`, `read_ops`, `write_ops`, `read_bytes`, and `file_size_bytes`. Keep the chronological partitions separate when interpreting the metrics: validation is used to choose the model setting; the test scores estimate performance on the later held-out period. The saved model defaults to `backend/algorithms/algo02/cache_model_results/cache_logreg_model.joblib`; pass `model_path=` to write it elsewhere. Confirm the chosen model artifact is available wherever the recommendation service runs.

### Code structure

The implementation is in [`backend/algorithms/algo02/`](../algo02/).

| File | Purpose |
| --- | --- |
| `ssd_policy.py` | Main recommendation pipeline |
| `inputs.py` | Input validation and goal thresholds |
| `candidates.py` | Latest-window validation and HDD candidate filtering |
| `prediction.py` | Feature extraction, chronological dataset splitting, model training, scoring, and benefit estimates |
| `greedy_selection.py` | Capacity-aware candidate selection and recommendation generation |
| `selection.py` | Selection compatibility exports |
| `demo.py` | Mock-only command-line example |
| `tests/` | Unit and regression tests |

Shared capacity, validation, and recommendation helpers are in [`backend/algorithms/common/`](../common/).

### Configuration

Policy settings are passed through `mode_config`; defaults are defined in `inputs.py`.

| Setting | Default |
| --- | --- |
| Goal | `performance` |
| Minimum read rate / minimum read fraction | 0.1 reads/s / 0.8 |
| Activity window / maximum age | 60–3,600 s / 300 s |
| SSD reserve | Greater of 1 GiB and 10% of total capacity |
| Maximum recommendations | 10 |
| Minimum model probability | Goal-dependent: 0.45 / 0.60 / 0.75 |

The model uses a ten-minute future label horizon, at least 15 future reads for a positive label, and the 70% / 15% / 15% chronological split by default. These training parameters can be changed when calling `train_val_test_model`.

### API and integration

CORE calls the policy through its existing five-argument interface:

```python
from backend.algorithms.algo02 import evaluate_ssd_caching_policy

recommendations = evaluate_ssd_caching_policy(
    devices=device_records,
    realtime={"host_id": host_id, "evaluation_time_utc": evaluation_time_utc},
    history={"file_activity": file_activity_records},
    mode_config={},
    capabilities=os_capabilities,
)
```

The input capability `file_access_metrics=True` is required. Activity rows need the host and file/device identity, file size, read/write counts, source, and UTC window timestamps. The policy returns recommendations with the original source retained, a proposed SSD target, approval requirements, and estimated scoring details. Cache population still depends on a separately supported and approved executor; the current policy does not perform that action.

## Non-Functional Requirements

- **Performance:** Candidate filtering and bounded, single-pass greedy selection keep recommendation work proportional to the number of activity records and candidates.
- **Reliability:** Input checks, freshness checks, duplicate-window handling, and explicit no-recommendation reasons make incomplete telemetry visible.
- **Maintainability:** Prediction, filtering, selection, and orchestration are separated into focused modules, with a stable policy entry point and unit tests.
- **Safety and explainability:** SSD reserves are applied before selection; recommendations preserve the source file and require approval. Estimated benefit and mock-data status are identified in the recommendation details.

## Current limitations

Model quality depends on sufficient representative activity history and properly completed future labels. The built-in cold-start model is based on synthetic anchors and is not evidence of real workload accuracy. The latency assumptions produce estimates rather than observed results. Cache population and coherency are outside the current policy implementation, so recommendations alone do not deliver a speedup.

## Related documentation

- [Project README](../../../README.md)
- [ALGO-01 documentation](policy_1_readme.md)
- [Project API contracts](../../../docs/api-contracts.md)