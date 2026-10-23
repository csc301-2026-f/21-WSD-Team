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

// Keep the latest five minutes of generated process samples.
// The graph can request a smaller window, such as one minute.
const HISTORY_WINDOW_MS = 5 * 60 * 1000;
const mockProcessHistoryRecords = [];

function generateProcessSample(process, now) {
    return {
        host_id: process.host_id,
        pid: process.pid,
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

    // Save each polling sample for historical queries.
    mockProcessHistoryRecords.push(...samples);

    pruneProcessHistory(now.getTime());

    return samples;
}

/* MOCK PROCESS HISTORY */

export function getMockProcessHistory({
    host_id,
    pid,
    start_time_utc,
    start_utc,
    end_utc,
    bucket_seconds
}) {
    if (
        !host_id ||
        pid === undefined ||
        pid === null ||
        !start_time_utc ||
        !start_utc ||
        !end_utc
    ) {
        throw new Error(
            "host_id, pid, start_time_utc, start_utc and end_utc are required"
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
                record.host_id === host_id &&
                record.pid === Number(pid) &&
                record.start_time_utc === start_time_utc &&
                timestamp >= start &&
                timestamp <= end
            );
        })
        .sort((a, b) =>
            Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc)
        );

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
