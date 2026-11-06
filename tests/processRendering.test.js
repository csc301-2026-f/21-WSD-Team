import test from "node:test";
import assert from "node:assert/strict";

import {
    getProcessRowValues,
    getEmptyStateMessage,
    getProcessStatusMessage
} from "../frontend/js/processRendering.js";

test("creates the correct values for a process row", () => {
    const process = {
        process_name: "chrome.exe",
        pid: 1234,
        read_bytes_per_sec: 2_000_000,
        write_bytes_per_sec: 500_000,
        attributed_device_id: "SSD-1"
    };

    assert.deepEqual(getProcessRowValues(process), [
        "chrome.exe",
        1234,
        "2.00 MB/s",
        "500.00 KB/s",
        "SSD-1"
    ]);
});

test("uses fallback values for missing process information", () => {
    const process = {};

    assert.deepEqual(getProcessRowValues(process), [
        "Unknown",
        "N/A",
        "N/A",
        "N/A",
        "Unattributed"
    ]);
});

test("formats zero read and write rates correctly", () => {
    const process = {
        process_name: "idle.exe",
        pid: 10,
        read_bytes_per_sec: 0,
        write_bytes_per_sec: 0,
        attributed_device_id: "SSD-1"
    };

    assert.deepEqual(getProcessRowValues(process), [
        "idle.exe",
        10,
        "0 B/s",
        "0 B/s",
        "SSD-1"
    ]);
});

test("shows no processes available when the process list is empty", () => {
    assert.equal(
        getEmptyStateMessage([]),
        "No processes available."
    );
});

test("shows no matching processes when the original list is not empty", () => {
    const processes = [
        { process_name: "chrome.exe", pid: 1234 }
    ];

    assert.equal(
        getEmptyStateMessage(processes),
        "No processes match your search."
    );
});

test("shows the total process count when no search is active", () => {
    const processes = [
        { process_name: "chrome.exe", pid: 1234 },
        { process_name: "explorer.exe", pid: 5678 }
    ];

    assert.equal(
        getProcessStatusMessage(processes),
        "2 processes detected."
    );
});

test("shows filtered and total counts when searching", () => {
    const processes = [
        { process_name: "chrome.exe", pid: 1234 },
        { process_name: "chrome.exe", pid: 5678 },
        { process_name: "explorer.exe", pid: 9012 }
    ];

    assert.equal(
        getProcessStatusMessage(processes, "chrome"),
        "Showing 2 of 3 processes."
    );
});

test("trims whitespace from the search term", () => {
    const processes = [
        { process_name: "chrome.exe", pid: 1234 }
    ];

    assert.equal(
        getProcessStatusMessage(processes, "   "),
        "1 processes detected."
    );
});

test("searches process IDs in the status count", () => {
    const processes = [
        { process_name: "chrome.exe", pid: 1234 },
        { process_name: "explorer.exe", pid: 5678 }
    ];

    assert.equal(
        getProcessStatusMessage(processes, "1234"),
        "Showing 1 of 2 processes."
    );
});