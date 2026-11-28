# Windows Backend: ETW decoding and file moving

The Windows backend decodes incoming file and disk events from the ETW library to give accurate metrics on disks, processes and all accessed files on system. It also takes in and executes file moving requests from the CORE level.

When requested by the CORE level, it aggregates the requested events for the last requested ammount of seconds into lists of all affected disks, processes, files, and their respective metrics. 

---

## 1. How It Works

### ETW event tracing
The Backend registers its decoding function to the ETW library as a callback for all disk and file events. This function runs on a thread not managed by WSD and thus a lock must be used when accessing the recorded events.

When decoding a diskIO event, its accessed file may be unknown, which is acceptable since a diskIO event is only used for disk metrics, thus not requiring it to know its file attribution.

When deciding a fileIO event, however, its disk number may be unknown, as well as its relative path, this is not acceptable as we need it to give a full path to core for each file. Thus we must correlate its fields to find a diskIO event its file corresponds to. The correlation path follows the following graph:

FileIO.r/w->FileKey ~ FileIO.name->FileObject ~ DiskIO.r/w->FileObject

FileIO.r/w->FileObject ~ stable FileID across FileIO

### Mount point and disk discovery
The windows backend uses the WMI library to cache relevant information about mount point, disks, offset bounds, and NT volume paths on startup, as getting such information while running would induce massive overhead.

It then offers access points to this data to CORE, the event decoder, and the file mover

### File moving
The dedicated file mover receives a move instruction from CORE with a source path, a destination mount point, and optionally a destination relative path, a process callback to report copy completion percentage in float, and a cancel callable that must return true when called if CORE wishes for the move to be cancelled. 

The move itself first copies the file to a temporary .moving file and then renames it to the desired name. If at any point an error occurs, the mover returns with an appropriate error code. If the error happens after the file has successfully been copied, this work is not thrown away, and instead the mover tries to finish the move once.

### D4 Relevant function calls

#### `create_backend(host_id) -> WindowsBackend`:
Returns a linked backend object to start, pass funciton calls, and close upon program end.

#### `backend.start()` , `backend.close()`:
Afforementioned start and close functions

#### `backend.get_devices() -> list[Device]`:
Returns the afformentioned cached device list.

#### `backend.get_device_metrics(sample_window_seconds) -> list[DeviceMetric]`:
Uses the cached device list to aggregate the diskIO events received in the last sample_window_seconds by.

#### `backend.get_process_metrics(sample_window_seconds) -> list[ProcessMetric]`:
Aggregates the FileIO events received in the last sample_window_seconds by their own reported process ID and start time as to differentiate processes that reused the same PID.

#### `backend.get_file_activity(sample_window_seconds,now_ns) -> list[FileActivity]`:
Aggregates the FileIO events received in the last sample_window_seconds by their recovered path.

#### `backend.file_mover.move_file(source_path,destination_mount,destination_rel_path,progress_callback,cancel_call) -> MoveResult`:
Tries to move a file from a source path to a destination mount, with optionally specified relative destination path, progress callback to be called with move progress ranging from 0.0 to 100.0 every 0.1 seconds, and a cancel callable to be set to true if the move is to be cancelled, also checked every 0.1 seconds.

---

## 2. Developer Guide

### Setup and Testing
The Windows backend requires Python 3.10+ ,and libraries: pywintrace, psutil, pywin32, and WMI.

To run the backend as a standalone with instructions in `__main__.py`:

```bash

python -m backend/windows

```

---

## 3. dataclasses
The cached devices' information is kept in the following dataclass

```python

@dataclass(frozen=True) 
class Device: #need: wmi
    host_id: str 
    device_id: int #disk_number
    display_name: str
    media_type: MediaType | None
    capacity_bytes: int | None
    free_bytes: int | None
    mount_points: list[str] #disk_letters
    is_available: bool

```

The following metrics are are returned to CORE:

```python

@dataclass(frozen=True)
class DeviceMetric:
    host_id: str
    device_id: int
    timestamp_utc: str
    sample_window_seconds: float

    read_bytes_per_sec: float | None
    write_bytes_per_sec: float | None
    read_iops: float | None
    write_iops: float | None
    avg_read_latency_ms: float | None
    avg_write_latency_ms: float | None

    source: str

```

```python

@dataclass(frozen=True)
class ProcessMetric:
    host_id: str
    pid: int
    start_time_utc: str | None
    process_name: str | None
    timestamp_utc: str
    sample_window_seconds: float

    read_bytes_per_sec: float | None
    write_bytes_per_sec: float | None
    attributed_device_id: str | None

```

```python

@dataclass(frozen=True)
class FileActivity:
    host_id: str
    file_id: str | None
    path: str | None
    device_id: int | None

    window_start_utc: str
    window_end_utc: str

    read_bytes: int | None
    write_bytes: int | None
    read_ops: int | None
    write_ops: int | None
    file_size_bytes: int | None

    source: str

```

Additionally, the Windows backend keeps IO events in this data class when not aggregated

```python

@dataclass(frozen=True)
class RawIoEvent:
    timestamp_ns: int
    operation: str

    pid: int | None
    process_start_time_utc: str | None
    process_name: str | None
    device_id: int | None
    transferred_bytes: int | None
    duration_ns: int | None
    file_id: int | None = None
    path: str | None = None
    decoded_drive_letter: str | None = None
    file_size_bytes: int | None = None
    file_attribution_verified: bool = False
    source: str = "windows_etw"

```

Finally, when a move operation returns, it reports its result, either with an error, or with the performed move information

```python

@dataclass(frozen=True)#field may be none if move_error is not none
class MoveResult:
    move_error: MoveError | None = None
    source_path: str | None = None
    destination_path: str | None = None
    bytes_moved: int | None = None
    total_bytes: int | None = None

```

MoveError contains a `code` attribute that explains how the move failed

```python

class MoveErrorCode(str, Enum):
    INVALID_SOURCE = "invalid_source"
    INVALID_DESTINATION = "invalid_destination"
    SOURCE_NOT_ON_MANAGED_DEVICE = "source_not_on_managed_device"
    DESTINATION_NOT_ON_MANAGED_DEVICE = "destination_not_on_managed_device"
    AMBIGUOUS_DEVICE = "ambiguous_device"
    SAME_FILE = "same_file"
    DESTINATION_EXISTS = "destination_exists"
    DESTINATION_PARENT_MISSING = "destination_parent_missing"
    MOVE_FAILED = "move_failed"
    MOVE_CANCELLED = "move_cancelled"
    COPPIED_BUT_ERRORED = "coppied_but_errored"

```

---

## 4. Non-Functional Requirements (NFRs)

- **Performance:** Decoding of ETW events happens with as little overhead as possible by using hashmaps for correlations.
- **Reliability and Fault Tolerance:** In case of an ETW event coming out of order or not being yet decodable with the aquired data, it is put in a queue that is sorted through upon aggregation to check for newly available data. Additionally, file moving results are reported through a left-right tuple of the shape `MoveResult(Err|None , Data|None)`
- **Maintainability:** Full separation of Windows backend from CORE module, only ever take python variables for function calls as well as Path variables for file moving.
- **Safety and Truthfulness:** Missing data either comes in the form of not returning any data for the given element or `None` being inserted in the non-required field.
- **Checkpoints:** File moving only ever unlinks the original file when the copy is confirmed to have been fully written on disk and renamed.

---

## 5. Current Limitations

1. **Missing Data:** Automatic 1-hour event pruning is currently triggered on each call by CORE. This means data that could not be correlated is lost after this period. This can happen when a FileIO event does not get a corresponding DiskIO event fired and thus cannot figure out its absolute path.
2. **File Moving:** If a file move fails for any reason, it may need an alternate way of moving it that is not implemented here as it may fail on successive attempts as well.

---

## 6. Related Documentation

- [Project README](../../README.md)
- [Project API Contracts](../../docs/api-contracts.md)
- [Windows Contracts](./contracts.py)
