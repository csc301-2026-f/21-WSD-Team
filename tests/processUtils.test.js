import { getProcessInstanceId } from "../frontend/js/processUtils.js";
import test from "node:test";
import assert from "node:assert/strict";

import {
    getProcessKey,
    formatRate,
    filterProcesses
} from "../frontend/js/processUtils.js";


const mockProcesses = [
    {
        host_id: "host_mock",
        pid: 4120,
        start_time_utc: "2026-10-21T15:00:00Z",
        process_name: "steam.exe"
    },
    {
        host_id: "host_mock",
        pid: 6210,
        start_time_utc: "2026-10-21T15:01:00Z",
        process_name: "chrome.exe"
    },
    {
        host_id: "host_mock",
        pid: 7350,
        start_time_utc: "2026-10-21T15:02:00Z",
        process_name: "Code.exe"
    }
];


/* PROCESS IDENTIFICATION */

test("generates a unique process key", () => {
    const key = getProcessKey(mockProcesses[0]);

    assert.equal(
        key,
        "host_mock:4120:2026-10-21T15:00:00Z"
    );
});


test("different process instances have different keys", () => {
    const firstKey = getProcessKey(mockProcesses[0]);
    const secondKey = getProcessKey(mockProcesses[1]);

    assert.notEqual(firstKey, secondKey);
});


/* RATE FORMATTING */

test("formats bytes per second", () => {
    assert.equal(formatRate(500), "500 B/s");
});


test("formats kilobytes per second", () => {
    assert.equal(formatRate(2500), "2.50 KB/s");
});


test("formats megabytes per second", () => {
    assert.equal(formatRate(5000000), "5.00 MB/s");
});


test("handles zero throughput", () => {
    assert.equal(formatRate(0), "0 B/s");
});


test("handles missing or invalid throughput", () => {
    assert.equal(formatRate(null), "N/A");
    assert.equal(formatRate(undefined), "N/A");
    assert.equal(formatRate(-100), "N/A");
    assert.equal(formatRate(Infinity), "N/A");
});


/* PROCESS SEARCH */

test("empty search returns all processes", () => {
    const result = filterProcesses(mockProcesses, "");

    assert.equal(result.length, 3);
});


test("searches processes by exact PID", () => {
    const result = filterProcesses(mockProcesses, "4120");

    assert.equal(result.length, 1);
    assert.equal(result[0].process_name, "steam.exe");
});


test("searches processes by partial process name", () => {
    const result = filterProcesses(mockProcesses, "steam");

    assert.equal(result.length, 1);
    assert.equal(result[0].pid, 4120);
});


test("search is case insensitive", () => {
    const result = filterProcesses(mockProcesses, "STEAM");

    assert.equal(result.length, 1);
    assert.equal(result[0].process_name, "steam.exe");
});


test("search supports partial PID matches", () => {
    const result = filterProcesses(mockProcesses, "12");

    assert.equal(result.length, 1);
    assert.equal(result[0].pid, 4120);
});


test("unmatched search returns an empty array", () => {
    const result = filterProcesses(mockProcesses, "firefox");

    assert.deepEqual(result, []);
});


test("search ignores surrounding whitespace", () => {
    const result = filterProcesses(mockProcesses, "  chrome  ");

    assert.equal(result.length, 1);
    assert.equal(result[0].pid, 6210);
});


test("invalid process input returns an empty array", () => {
    assert.deepEqual(filterProcesses(null, "steam"), []);
});

test("matches the backend process ID when start time is null", () => {
    assert.equal(
        getProcessInstanceId({
            pid: 1234,
            start_time_utc: null
        }),
        "1234_None"
    );
});

test("includes the start time in the process instance ID", () => {
    assert.equal(
        getProcessInstanceId({
            pid: 1234,
            start_time_utc: "2026-11-04T12:00:00Z"
        }),
        "1234_2026-11-04T12:00:00Z"
    );
});