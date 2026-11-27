// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
/* LIVE-SIMULATED DISK METRICS */
export const mockDevices = [
    {
        host_id: "host_mock",
        device_id: "disk_123",
        display_name: "Fake Samsung SSD 980",
        media_type: "ssd",
        capacity_bytes: 1000000000000,
        free_bytes: 350000000000,
        mount_points: ["C:"],
        is_available: true
    },
    {
        host_id: "host_mock",
        device_id: "disk_456",
        display_name: "Fake Storage HDD",
        media_type: "hdd",
        capacity_bytes: 2000000000000,
        free_bytes: 1400000000000,
        mount_points: ["D:"],
        is_available: true
    },
    {
        host_id: "host_mock",
        device_id: "disk_789",
        display_name: "Fake Crucial P5 Plus NVMe",
        media_type: "ssd",
        capacity_bytes: 1000000000000,
        free_bytes: 100000000000,
        mount_points: ["E:"],
        is_available: true
    },
    {
        host_id: "host_mock",
        device_id: "disk_101",
        display_name: "Fake Seagate External HDD",
        media_type: "hdd",
        capacity_bytes: 4000000000000,
        free_bytes: 3000000000000,
        mount_points: ["F:"],
        is_available: true
    }
];

// Stable baseline values. The generator fluctuates around these.
const baseMockMetrics = [
    {
        host_id: "host_mock",
        device_id: "disk_123",
        read_bytes_per_sec: 1919810,
        write_bytes_per_sec: 114514,
        read_iops: 150.5,
        write_iops: 40,
        avg_read_latency_ms: 1.8,
        avg_write_latency_ms: 2.2
    },
    {
        host_id: "host_mock",
        device_id: "disk_456",
        read_bytes_per_sec: 800000,
        write_bytes_per_sec: 100000,
        read_iops: 120,
        write_iops: 20,
        avg_read_latency_ms: 3.5,
        avg_write_latency_ms: 4.1
    }
];

function fluctuate(value, variation = 0.15) {
    // Random change around the current baseline.
    const factor = 1 + (Math.random() * 2 - 1) * variation;
    return Math.max(0, value * factor);
}

function round(value, decimals = 0) {
    const scale = 10 ** decimals;
    return Math.round(value * scale) / scale;
}

export function getMockMetrics() {
    const now = new Date().toISOString();

    return baseMockMetrics.map(metric => ({
        ...metric,
        timestamp_utc: now,
        sample_window_seconds: 2,
        read_bytes_per_sec: round(fluctuate(metric.read_bytes_per_sec)),
        write_bytes_per_sec: round(fluctuate(metric.write_bytes_per_sec)),
        read_iops: round(fluctuate(metric.read_iops), 1),
        write_iops: round(fluctuate(metric.write_iops), 1),
        avg_read_latency_ms: round(fluctuate(metric.avg_read_latency_ms, 0.2), 2),
        avg_write_latency_ms: round(fluctuate(metric.avg_write_latency_ms, 0.2), 2),
        source: "mock-live"
    }));
}

/* LIVE-SIMULATED PROCESS METRICS */

const baseMockProcesses = [
    {
        host_id: "host_mock",
        pid: 4120,
        start_time_utc: "2026-10-21T15:00:00Z",
        process_name: "steam.exe",
        attributed_device_id: "disk_123",
        base_read_bytes_per_sec: 12500000,
        base_write_bytes_per_sec: 1800000
    },
    {
        host_id: "host_mock",
        pid: 6210,
        start_time_utc: "2026-10-21T15:01:00Z",
        process_name: "chrome.exe",
        attributed_device_id: "disk_123",
        base_read_bytes_per_sec: 4200000,
        base_write_bytes_per_sec: 650000
    },
    {
        host_id: "host_mock",
        pid: 7350,
        start_time_utc: "2026-10-21T15:02:00Z",
        process_name: "Code.exe",
        attributed_device_id: "disk_456",
        base_read_bytes_per_sec: 2100000,
        base_write_bytes_per_sec: 3100000
    },
    {
        host_id: "host_mock",
        pid: 1820,
        start_time_utc: "2026-10-21T15:03:00Z",
        process_name: "explorer.exe",
        attributed_device_id: null,
        base_read_bytes_per_sec: 350000,
        base_write_bytes_per_sec: 90000
    }
];

// Retain five minutes of process history.
const HISTORY_WINDOW_MS = 5 * 60 * 1000;
const mockProcessHistoryRecords = [];

// Must match the process_instance_id format used by the frontend/backend.
function getProcessInstanceId(process) {
    return `${process.pid}_${process.start_time_utc ?? ""}`;
}

function generateProcessSample(process, now) {
    return {
        host_id: process.host_id,
        pid: process.pid,
        process_instance_id: getProcessInstanceId(process),
        start_time_utc: process.start_time_utc,
        process_name: process.process_name,
        timestamp_utc: now.toISOString(),
        sample_window_seconds: 2,
        read_bytes_per_sec: round(
            fluctuate(process.base_read_bytes_per_sec, 0.3)
        ),
        write_bytes_per_sec: round(
            fluctuate(process.base_write_bytes_per_sec, 0.3)
        ),
        attributed_device_id: process.attributed_device_id
    };
}

function pruneProcessHistory(nowMs) {
    const cutoff = nowMs - HISTORY_WINDOW_MS;

    while (
        mockProcessHistoryRecords.length > 0 &&
        Date.parse(mockProcessHistoryRecords[0].timestamp_utc) < cutoff
    ) {
        mockProcessHistoryRecords.shift();
    }
}

export function getMockProcesses() {
    const now = new Date();

    const samples = baseMockProcesses.map(process =>
        generateProcessSample(process, now)
    );

    // Accumulate samples for historical queries.
    mockProcessHistoryRecords.push(...samples);

    pruneProcessHistory(now.getTime());

    return samples;
}

/* MOCK PROCESS HISTORY */

export function getMockProcessHistory({
    process_instance_id,
    start_utc,
    end_utc,
    bucket_seconds
}) {
    if (!process_instance_id || !start_utc || !end_utc) {
        throw new Error(
            "process_instance_id, start_utc and end_utc are required"
        );
    }

    const start = Date.parse(start_utc);
    const end = Date.parse(end_utc);

    if (
        !Number.isFinite(start) ||
        !Number.isFinite(end) ||
        start > end
    ) {
        throw new Error("Invalid history time range");
    }

    let records = mockProcessHistoryRecords
        .filter(record => {
            const timestamp = Date.parse(record.timestamp_utc);

            return (
                record.process_instance_id === process_instance_id &&
                timestamp >= start &&
                timestamp <= end
            );
        })
        .sort((a, b) =>
            Date.parse(a.timestamp_utc) -
            Date.parse(b.timestamp_utc)
        );

    // Optional time-bucket aggregation.
    if (bucket_seconds !== undefined && bucket_seconds !== null) {
        const seconds = Number(bucket_seconds);

        if (!Number.isInteger(seconds) || seconds <= 0) {
            throw new Error("bucket_seconds must be a positive integer");
        }

        const buckets = new Map();

        for (const record of records) {
            const timestamp = Date.parse(record.timestamp_utc);
            const bucketStart =
                Math.floor(timestamp / (seconds * 1000)) *
                seconds * 1000;

            if (!buckets.has(bucketStart)) {
                buckets.set(bucketStart, record);
            }
        }

        records = [...buckets.values()];
    }

    return records;
}

/* MOCK FILE ACTIVITY */

const mockFileActivityBase = [
    { file_id: "mock-file-chrome-cache-001", path: "C:\\Users\\Danny\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache\\Cache_Data\\f_000123", device_id: "disk_123", read_bytes: 18432000, write_bytes: 131072, read_ops: 180, write_ops: 8, file_size_bytes: 20971520 },
    { file_id: "mock-file-chrome-history-002", path: "C:\\Users\\Danny\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History", device_id: "disk_123", read_bytes: 61440, write_bytes: 8192, read_ops: 49, write_ops: 14, file_size_bytes: 8388608 },
    { file_id: "mock-file-meeting-doc-003", path: "C:\\Users\\Danny\\Documents\\Project\\Sprint Planning.docx", device_id: "disk_123", read_bytes: 1258291, write_bytes: 32768, read_ops: 18, write_ops: 4, file_size_bytes: 870400 },
    { file_id: "mock-file-installer-004", path: "D:\\Downloads\\VisualStudioSetup.exe", device_id: "disk_456", read_bytes: 268435456, write_bytes: 0, read_ops: 1024, write_ops: 0, file_size_bytes: 536870912 },
    { file_id: "mock-file-vscode-log-005", path: "C:\\Users\\Danny\\AppData\\Roaming\\Code\\logs\\20261124T101500\\window1\\renderer.log", device_id: "disk_123", read_bytes: 460800, write_bytes: 3211264, read_ops: 120, write_ops: 840, file_size_bytes: 2293760 },
    { file_id: "mock-file-project-source-006", path: "D:\\Projects\\WSD\\frontend\\js\\fileIoMonitoring.js", device_id: "disk_456", read_bytes: 8388608, write_bytes: 204800, read_ops: 100, write_ops: 7, file_size_bytes: 36864 },
    { file_id: "mock-file-app-database-007", path: "C:\\Users\\Danny\\AppData\\Local\\WSD\\metrics.sqlite", device_id: "disk_123", read_bytes: 12582912, write_bytes: 5242880, read_ops: 420, write_ops: 190, file_size_bytes: 125829120 },
    { file_id: "mock-file-game-archive-008", path: "E:\\SteamLibrary\\steamapps\\common\\Example Game\\Content\\pakchunk0-Windows.pak", device_id: "disk_789", read_bytes: 707788800, write_bytes: 524288, read_ops: 1280, write_ops: 12, file_size_bytes: 1932735283 },
    { file_id: "mock-file-user-settings-009", path: "C:\\Users\\Danny\\AppData\\Roaming\\Code\\User\\settings.json", device_id: "disk_123", read_bytes: 16384, write_bytes: 4096, read_ops: 8, write_ops: 2, file_size_bytes: 9216 },
    { file_id: "mock-file-npm-cache-010", path: "D:\\Users\\Danny\\AppData\\Local\\npm-cache\\_cacache\\content-v2\\sha512\\8f\\package.tgz", device_id: "disk_456", read_bytes: 4194304, write_bytes: 1048576, read_ops: 32, write_ops: 10, file_size_bytes: 7340032 },
    { file_id: "mock-file-cloud-document-011", path: "C:\\Users\\Danny\\OneDrive\\Research\\Storage Benchmark.xlsx", device_id: "disk_123", read_bytes: 32768, write_bytes: 0, read_ops: 3, write_ops: 0, file_size_bytes: 524288 },
    { file_id: "mock-file-app-log-012", path: "C:\\ProgramData\\WSD\\Logs\\collector.log", device_id: "disk_456", read_bytes: 4096, write_bytes: 28672, read_ops: 2, write_ops: 18, file_size_bytes: 131072 }
];

export function getMockFileActivity() {
    const windowEnd = new Date();
    const windowStart = new Date(windowEnd.getTime() - 8000);
    return mockFileActivityBase.map(record => ({
        host_id: "host_mock",
        ...record,
        window_start_utc: windowStart.toISOString(),
        window_end_utc: windowEnd.toISOString(),
        source: "mock:file-io-preview"
    }));
}
