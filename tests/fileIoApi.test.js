import test from "node:test";
import assert from "node:assert/strict";

import { getLatestFileActivity, getLatestProcesses, isMockDataEnabled, setMockDataEnabled } from "../frontend/js/api.js";
import { filterAndSortFileActivity, normalizeFileActivity, summarizeFileActivity } from "../frontend/js/fileIoApi.js";

test("normalizes documented FileActivity windows and derives measured rates", () => {
    const [file] = normalizeFileActivity([{
        file_id: "file-1",
        path: "C:\\data\\report.csv",
        device_id: 3,
        window_start_utc: "2026-11-22T10:00:00Z",
        window_end_utc: "2026-11-22T10:00:10Z",
        read_bytes: 4096,
        write_bytes: 1024,
        read_ops: 4,
        write_ops: 1,
        file_size_bytes: 8192,
        source: "os-agent"
    }]);

    assert.equal(file.name, "report.csv");
    assert.equal(file.deviceId, "3");
    assert.equal(file.durationSeconds, 10);
    assert.equal(file.readBytesPerSec, 409.6);
    assert.equal(file.writeBytesPerSec, 102.4);
    assert.equal(file.readOpsPerSec, 0.4);
    assert.equal(file.writeOpsPerSec, 0.1);
    assert.equal(file.totalBytesPerSec, 512);
    assert.equal(file.lastActivity, "2026-11-22T10:00:10Z");
});

test("keeps unavailable fields null and rejects invalid time windows for derived rates", () => {
    const [file] = normalizeFileActivity([{
        path: "/var/log/app.log",
        window_start_utc: "not-a-time",
        window_end_utc: "also-not-a-time",
        read_bytes: 100,
        write_bytes: null,
        read_ops: 2,
        write_ops: null
    }]);

    assert.equal(file.name, "app.log");
    assert.equal(file.readBytes, 100);
    assert.equal(file.readBytesPerSec, null);
    assert.equal(file.readOpsPerSec, null);
    assert.equal(file.writeBytesPerSec, null);
    assert.equal(file.totalBytesPerSec, null);
    assert.equal(file.lastActivity, null);
});

test("adapts nested Linux file metrics without inventing a measurement window", () => {
    const [file] = normalizeFileActivity([{
        host_id: "host-1",
        file: { absolute_path: "/var/log/service.log", inode: 42, device: 2049 },
        timestamp: "2026-11-22T10:00:08Z",
        duration: 8,
        read_completed_bytes: 160,
        write_completed_bytes: 0,
        read_success_ops: 2,
        write_success_ops: 0,
        source: "linux-ebpf"
    }]);

    assert.equal(file.hostId, "host-1");
    assert.equal(file.fileId, "42");
    assert.equal(file.path, "/var/log/service.log");
    assert.equal(file.name, "service.log");
    assert.equal(file.deviceId, "2049");
    assert.equal(file.readBytes, 160);
    assert.equal(file.writeBytes, 0);
    assert.equal(file.readOps, 2);
    assert.equal(file.writeOps, 0);
    assert.equal(file.readBytesPerSec, null);
    assert.equal(file.lastActivity, "2026-11-22T10:00:08Z");
});

test("uses the latest file activity endpoint and shared success envelope", async () => {
    const originalFetch = globalThis.fetch;
    let requestedUrl;
    setMockDataEnabled(false);
    globalThis.fetch = async url => {
        requestedUrl = String(url);
        return {
            ok: true,
            json: async () => ({ status: "success", data: [], error: null })
        };
    };

    try {
        assert.deepEqual(await getLatestFileActivity(), []);
        assert.equal(requestedUrl, "/api/v1/files/activity/latest");
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test("rejects an unavailable file activity endpoint", async () => {
    const originalFetch = globalThis.fetch;
    setMockDataEnabled(false);
    globalThis.fetch = async () => ({
        ok: false,
        status: 404,
        json: async () => ({ status: "error", error: { code: "NOT_FOUND", message: "Endpoint Not Found" } })
    });

    try {
        await assert.rejects(getLatestFileActivity(), /HTTP error 404/);
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test("mock mode supplies realistic file records without calling the backend", async () => {
    const originalFetch = globalThis.fetch;
    setMockDataEnabled(true);
    globalThis.fetch = async () => {
        throw new Error("Mock mode must not make a live request.");
    };

    try {
        const records = await getLatestFileActivity();
        const rows = normalizeFileActivity(records);
        const summary = summarizeFileActivity(rows);

        assert.equal(isMockDataEnabled(), true);
        assert.equal(records.length, 12);
        assert.equal(new Set(records.map(record => record.file_id)).size, 12);
        assert.ok(records.every(record => record.source === "mock:file-io-preview"));
        assert.ok(records.some(record => record.path.includes("Chrome")));
        assert.ok(records.some(record => record.path.includes("Documents")));
        assert.ok(records.some(record => record.path.includes(".sqlite")));
        assert.equal(summary.fileCount, records.length);
        assert.equal(summary.totalReadBytes, records.reduce((sum, record) => sum + record.read_bytes, 0));
        assert.equal(summary.totalWriteBytes, records.reduce((sum, record) => sum + record.write_bytes, 0));
        assert.equal(summary.totalReadOps, records.reduce((sum, record) => sum + record.read_ops, 0));
        assert.equal(summary.totalWriteOps, records.reduce((sum, record) => sum + record.write_ops, 0));
        assert.equal(summary.mostActiveFile.path, "E:\\SteamLibrary\\steamapps\\common\\Example Game\\Content\\pakchunk0-Windows.pak");
        assert.ok(rows.every(row => row.durationSeconds === 8));
        assert.equal(filterAndSortFileActivity(rows, { query: "fileIoMonitoring.js" }).length, 1);
        assert.equal(filterAndSortFileActivity(rows, { query: "SteamLibrary" })[0].fileId, "mock-file-game-archive-008");
        assert.equal(filterAndSortFileActivity(rows, { activity: "write" }).some(row => row.fileId === "mock-file-installer-004"), false);
        assert.equal(filterAndSortFileActivity(rows, { sort: "read_bytes" })[0].fileId, "mock-file-game-archive-008");
        assert.equal(filterAndSortFileActivity(rows, { sort: "write_bytes" })[0].fileId, "mock-file-app-database-007");
    } finally {
        setMockDataEnabled(false);
        globalThis.fetch = originalFetch;
    }
});

test("the shared mock setting continues to serve Process I/O mocks", async () => {
    const originalFetch = globalThis.fetch;
    setMockDataEnabled(true);
    globalThis.fetch = async () => {
        throw new Error("Shared mock mode must not make a process API request.");
    };

    try {
        const processes = await getLatestProcesses();
        assert.equal(isMockDataEnabled(), true);
        assert.ok(processes.length > 0);
        assert.ok(processes.every(process => process.host_id === "host_mock"));
    } finally {
        setMockDataEnabled(false);
        globalThis.fetch = originalFetch;
    }
});

test("summary keeps unavailable values distinct from empty or missing measurements", () => {
    const [partial] = normalizeFileActivity([{
        file_id: "file-partial",
        read_bytes: 100,
        write_bytes: null,
        read_ops: 2,
        write_ops: null
    }]);
    const partialSummary = summarizeFileActivity([partial]);
    assert.equal(partialSummary.totalReadBytes, 100);
    assert.equal(partialSummary.totalWriteBytes, null);
    assert.equal(partialSummary.totalReadOps, 2);
    assert.equal(partialSummary.totalWriteOps, null);
    assert.equal(partialSummary.mostActiveFile, null);

    const emptySummary = summarizeFileActivity([]);
    assert.equal(emptySummary.fileCount, 0);
    assert.equal(emptySummary.totalReadBytes, null);
    assert.equal(emptySummary.totalReadOps, null);
});

test("requires an array of file activity records", () => {
    assert.throws(() => normalizeFileActivity(null), /array of FileActivity records/);
    assert.deepEqual(normalizeFileActivity([]), []);
});
