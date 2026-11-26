import test from "node:test";
import assert from "node:assert/strict";
import {
    buildFileActivityHistory,
    createRollingFileActivityHistory,
    rankFileActivity
} from "../frontend/js/fileIoHistory.js";

function row(fileId, endMs, values = {}) {
    return {
        fileId,
        path: `/data/${fileId}.bin`,
        name: `${fileId}.bin`,
        windowStartUtc: new Date(endMs - 8000).toISOString(),
        windowEndUtc: new Date(endMs).toISOString(),
        durationSeconds: 8,
        readBytes: 0,
        writeBytes: 0,
        readOps: 0,
        writeOps: 0,
        ...values
    };
}

test("rolling file history deduplicates identical windows and expires old samples", () => {
    const history = createRollingFileActivityHistory(300_000);
    const firstEnd = Date.parse("2026-11-26T12:00:08Z");
    const first = row("a", firstEnd, { readBytes: 800 });

    assert.equal(history.record([first], firstEnd), true);
    assert.equal(history.record([first], firstEnd + 1), false);
    assert.equal(history.getObservations(firstEnd + 299_999).length, 1);
    assert.equal(history.getObservations(firstEnd + 300_001).length, 0);
});

test("window totals are converted to per-window rates without subtracting samples", () => {
    const firstEnd = Date.parse("2026-11-26T12:00:08Z");
    const series = buildFileActivityHistory([
        { timestamp: firstEnd, rows: [row("a", firstEnd, { readBytes: 800, writeBytes: 400, readOps: 8, writeOps: 4 })] },
        { timestamp: firstEnd + 5000, rows: [row("a", firstEnd + 5000, { readBytes: 1600, writeBytes: 800, readOps: 16, writeOps: 8 })] }
    ]);

    assert.equal(series[0].readBytesPerSecond, 100);
    assert.equal(series[0].writeBytesPerSecond, 50);
    assert.equal(series[0].totalBytesPerSecond, 150);
    assert.equal(series[0].readOpsPerSecond, 1);
    assert.equal(series[0].writeOpsPerSecond, 0.5);
    assert.equal(series[1].readBytesPerSecond, 200);
    assert.equal(series[1].totalBytesPerSecond, 300);
});

test("missing values remain unavailable rather than becoming zero", () => {
    const end = Date.parse("2026-11-26T12:00:08Z");
    const series = buildFileActivityHistory([
        { timestamp: end, rows: [row("a", end, { readBytes: null, writeBytes: 40, readOps: null, writeOps: 2 })] },
        { timestamp: end + 5000, rows: [] }
    ]);

    assert.equal(series[0].readBytesPerSecond, null);
    assert.equal(series[0].writeBytesPerSecond, 5);
    assert.equal(series[0].totalBytesPerSecond, null);
    assert.equal(series[0].readOpsPerSecond, null);
    assert.equal(series[0].writeOpsPerSecond, 0.25);
    assert.equal(series[1].readBytesPerSecond, null);
    assert.equal(series[1].writeBytesPerSecond, null);
});

test("most-active ranking averages available observations and does not count disappearance as zero", () => {
    const end = Date.parse("2026-11-26T12:00:08Z");
    const ranked = rankFileActivity([
        { timestamp: end, rows: [row("a", end, { readBytes: 800 }), row("b", end, { readBytes: 640 })] },
        { timestamp: end + 5000, rows: [row("b", end + 5000, { readBytes: 640 })] }
    ]);

    assert.equal(ranked[0].key, "a");
    assert.equal(ranked[0].averageBytesPerSecond, 100);
    assert.equal(ranked[1].key, "b");
    assert.equal(ranked[1].averageBytesPerSecond, 80);
});

test("a cache can be cleared independently for source-mode isolation", () => {
    const live = createRollingFileActivityHistory();
    const preview = createRollingFileActivityHistory();
    const end = Date.parse("2026-11-26T12:00:08Z");
    live.record([row("live", end)], end);
    preview.record([row("mock", end)], end);

    assert.deepEqual(live.getObservations(end)[0].rows.map(item => item.fileId), ["live"]);
    assert.deepEqual(preview.getObservations(end)[0].rows.map(item => item.fileId), ["mock"]);
    live.clear();
    assert.equal(live.getObservations(end).length, 0);
    assert.equal(preview.getObservations(end).length, 1);
});
