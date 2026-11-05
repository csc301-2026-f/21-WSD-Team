
import test from "node:test";
import assert from "node:assert/strict";

import {
    getMockProcesses,
    getMockProcessHistory
} from "../frontend/js/mockData.js";


test("mock process generation returns four processes", () => {
    const processes = getMockProcesses();

    assert.equal(processes.length, 4);
});


test("every mock process has the required identity fields", () => {
    const processes = getMockProcesses();

    for (const process of processes) {
        assert.equal(typeof process.host_id, "string");
        assert.equal(typeof process.pid, "number");
        assert.equal(typeof process.process_instance_id, "string");
        assert.equal(typeof process.process_name, "string");
        assert.ok(process.process_instance_id.length > 0);
    }
});


test("mock processes contain valid I/O metrics", () => {
    const processes = getMockProcesses();

    for (const process of processes) {
        assert.ok(Number.isFinite(process.read_bytes_per_sec));
        assert.ok(Number.isFinite(process.write_bytes_per_sec));

        assert.ok(process.read_bytes_per_sec >= 0);
        assert.ok(process.write_bytes_per_sec >= 0);
    }
});


test("generated samples can be retrieved from process history", () => {
    const start = new Date(Date.now() - 1000).toISOString();

    const processes = getMockProcesses();

    const end = new Date(Date.now() + 1000).toISOString();

    const selectedProcess = processes[0];

    const history = getMockProcessHistory({
        process_instance_id: selectedProcess.process_instance_id,
        start_utc: start,
        end_utc: end
    });

    assert.ok(history.length >= 1);

    for (const record of history) {
        assert.equal(
            record.process_instance_id,
            selectedProcess.process_instance_id
        );
    }
});


test("history queries do not return samples outside the requested time range", () => {
    const processes = getMockProcesses();

    const selectedProcess = processes[0];

    // Request a historical window that ends before the current samples.
    const end = new Date(Date.now() - 60_000).toISOString();
    const start = new Date(Date.now() - 120_000).toISOString();

    const history = getMockProcessHistory({
        process_instance_id: selectedProcess.process_instance_id,
        start_utc: start,
        end_utc: end
    });

    assert.equal(history.length, 0);
});


test("history queries reject invalid time ranges", () => {
    assert.throws(
        () => getMockProcessHistory({
            process_instance_id: "4120_2026-10-21T15:00:00Z",
            start_utc: "invalid-date",
            end_utc: new Date().toISOString()
        }),
        /Invalid history time range/
    );
});
