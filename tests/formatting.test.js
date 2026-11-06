
import test from "node:test";
import assert from "node:assert/strict";

import {
    calculateUsedPercent,
    formatMBps,
    formatIops,
    formatAverageLatency,
    getValidMetricValues,
    sumMetricValues
} from "../frontend/js/formatting.js";


test("calculates drive usage percentage", () => {
    assert.equal(calculateUsedPercent(1000, 250), 75);
});


test("returns zero percent when drive is empty", () => {
    assert.equal(calculateUsedPercent(1000, 1000), 0);
});


test("returns null for invalid drive capacity", () => {
    assert.equal(calculateUsedPercent(0, 0), null);
    assert.equal(calculateUsedPercent(1000, 1200), null);
    assert.equal(calculateUsedPercent(1000, -1), null);
});


test("converts bytes per second into MB/s", () => {
    assert.equal(formatMBps(5_000_000), "5.00 MB/s");
});


test("formats zero throughput correctly", () => {
    assert.equal(formatMBps(0), "0.00 MB/s");
});


test("rejects invalid throughput values", () => {
    assert.equal(formatMBps(null), "Not provided");
    assert.equal(formatMBps(-100), "Not provided");
    assert.equal(formatMBps(Infinity), "Not provided");
});


test("formats IOPS values", () => {
    assert.equal(formatIops(150.5), "150.5");
    assert.equal(formatIops(40), "40");
});


test("rejects invalid IOPS values", () => {
    assert.equal(formatIops(null), "Not provided");
    assert.equal(formatIops(-5), "Not provided");
});


test("calculates average latency", () => {
    assert.equal(
        formatAverageLatency([2, 4, 6]),
        "4.00 ms"
    );
});


test("handles missing latency measurements", () => {
    assert.equal(formatAverageLatency([]), "Not provided");
    assert.equal(
        formatAverageLatency([null, undefined, NaN]),
        "Not provided"
    );
});


test("extracts only valid metric values", () => {
    const metrics = [
        { read_iops: 100 },
        { read_iops: 150 },
        { read_iops: null },
        { read_iops: -10 },
        { read_iops: "200" }
    ];

    assert.deepEqual(
        getValidMetricValues(metrics, "read_iops"),
        [100, 150]
    );
});


test("sums valid metric values", () => {
    const metrics = [
        { read_bytes_per_sec: 1000000 },
        { read_bytes_per_sec: 2000000 },
        { read_bytes_per_sec: null }
    ];

    assert.equal(
        sumMetricValues(metrics, "read_bytes_per_sec"),
        3000000
    );
});
