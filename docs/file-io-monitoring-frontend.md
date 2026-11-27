# File I/O Monitoring Frontend Integration

## Current implementation status

The File I/O Monitoring page loads `/api/v1/files/activity/latest` and reads `/api/v1/capabilities` to display monitoring support. It refreshes file activity while the page is active.

Linux monitors files or folders selected through tracking subscriptions. Windows collects file activity through ETW. Process totals are not used as per-file measurements.

The frontend adapter uses the `FileActivity` fields in [API Contracts](api-contracts.md) §02.1:

| Field | Frontend use |
| --- | --- |
| `host_id` | Host associated with the observation |
| `file_id` | Stable file identity, when available |
| `path` | Display, search, and path-based selection |
| `device_id` | File's associated device, when verified |
| `window_start_utc`, `window_end_utc` | Measurement interval and last activity |
| `read_bytes`, `write_bytes` | Derive byte throughput using the measured interval |
| `read_ops`, `write_ops` | Derive operation rates using the measured interval |
| `file_size_bytes` | Optional detail |
| `source` | Measurement provenance |

The documented shape has no process name or process ID. Those fields remain unavailable in this view. Charts accumulate the last five minutes of observations in browser memory; reloading the page starts a new series.

## Frontend response structure

`GET /api/v1/files/activity/latest` returns the Flask envelope with an array of `FileActivity` records:

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

The values above are illustrative. Empty activity returns `data: []`.

## File subscriptions and history

Linux tracking subscriptions use these implemented routes:

- `GET /api/v1/files/subscriptions` — list active subscriptions.
- `POST /api/v1/files/subscriptions` — track an existing file or folder using `{"path": "/absolute/path"}`.
- `DELETE /api/v1/files/subscriptions` — stop tracking the supplied path.

The proposed `GET /api/v1/files/{file_id}/history?start_utc=...&end_utc=...&bucket_seconds=...` route is not implemented. The current charts use the page's observations rather than querying stored file history.

## Frontend modules

- `frontend/js/api.js` calls the capability, file activity and subscription endpoints.
- `frontend/js/fileIoApi.js` normalizes `FileActivity` rows and derives rates from their observation windows.
- `frontend/js/fileIoMonitoring.js` owns filtering, sorting, formatting, detail rendering, and reusable table/chart update entry points.
- `frontend/js/fileIoHistory.js` keeps the page's recent observations for the charts.
- `frontend/html/file_io.html` presents unavailable, empty, loading, table, detail, and chart states.
