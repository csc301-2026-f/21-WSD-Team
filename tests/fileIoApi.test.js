import test from "node:test";
import assert from "node:assert/strict";

import { normalizeFileActivity } from "../frontend/js/fileIoApi.js";

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

test("requires an array of file activity records", () => {
    assert.throws(() => normalizeFileActivity(null), /array of FileActivity records/);
});
