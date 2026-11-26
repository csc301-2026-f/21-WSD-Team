# File I/O Monitoring Frontend Integration

## Current implementation status

The File I/O Monitoring page is frontend-only. The current Flask API does not expose a file activity or file history endpoint. The page reads `/api/v1/capabilities` to display the backend's `file_access_metrics` flag, but it does not guess or call a file endpoint that does not exist.

The API currently exposes device and process measurements and process history. Process metrics are not per-file measurements and are never used to populate this page.

The proposed OS-level `FileActivity` shape in the draft `docs/api-contracts.md` §02.1 is the source for the frontend adapter. The contracts document is not an approved HTTP contract:

| Field | Frontend use |
| --- | --- |
| `host_id` | Host context, if needed by a future endpoint |
| `file_id` | Stable file identity, when available |
| `path` | Display, search, and path-based selection |
| `device_id` | File's associated device, when verified |
| `window_start_utc`, `window_end_utc` | Measurement interval and last activity |
| `read_bytes`, `write_bytes` | Derive byte throughput using the measured interval |
| `read_ops`, `write_ops` | Derive operation rates using the measured interval |
| `file_size_bytes` | Optional detail |
| `source` | Measurement provenance |

The documented shape has no process name or process ID. Those fields remain unavailable in this view. Historical graphs need multiple distinct activity windows per file.

## Proposed frontend response structure

No file HTTP response is currently documented. When a route is agreed, the frontend expects the existing Flask envelope with an array of documented `FileActivity` records:

```json
{
  "status": "success",
  "data": [
    {
      "host_id": "host-id",
      "file_id": "stable-file-id",
      "path": "/example/file.txt",
      "device_id": "device-id",
      "window_start_utc": "2026-11-22T10:00:00Z",
      "window_end_utc": "2026-11-22T10:00:10Z",
      "read_bytes": 4096,
      "write_bytes": 1024,
      "read_ops": 4,
      "write_ops": 1,
      "file_size_bytes": 8192,
      "source": "os-agent"
    }
  ],
  "error": null
}
```

This example documents the frontend adapter shape; it is not a live response or a backend implementation.

## API work required before live integration

The routes below are proposals only and are not currently implemented:

- `GET /api/v1/files/activity?window_seconds=...` — latest verified per-file activity windows for the table and summary.
- `GET /api/v1/files/{file_id}/history?start_utc=...&end_utc=...&bucket_seconds=...` — time series for the selected file's charts.

Both routes should return the standard success/error envelope and the `FileActivity` fields above. The activity route must report only verified file-level measurements and define how duplicate records, unknown paths, unsupported platforms, and empty results behave. The history route must return time-ordered windows. If process attribution is later supported, add explicit process identity fields to an accepted contract; do not infer them from unrelated process totals.

## Frontend modules

- `frontend/js/fileIoApi.js` reads the existing capability endpoint and normalizes documented `FileActivity` rows. It intentionally has no file data URL until a real route exists.
- `frontend/js/fileIoMonitoring.js` owns filtering, sorting, formatting, detail rendering, and reusable table/chart update entry points.
- `frontend/html/file_io.html` presents unavailable, empty, loading, table, detail, and chart states.
