// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only

export const FILE_ACTIVITY_HISTORY_WINDOW_MS = 5 * 60 * 1000;

const validCount = value => typeof value === "number" && Number.isFinite(value) && value >= 0;

function timestamp(value) {
    if (typeof value !== "string" || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
}

function rateFor(row, field) {
    if (!validCount(row[field]) || !validCount(row.durationSeconds) || row.durationSeconds === 0) {
        return null;
    }
    return row[field] / row.durationSeconds;
}

/**
 * In-memory rolling history of the latest file activity windows.
 * API counters are per-window totals, not cumulative counters: each snapshot
 * is retained as a rate sample and is never subtracted from the previous one.
 */
export function createRollingFileActivityHistory(windowMs = FILE_ACTIVITY_HISTORY_WINDOW_MS) {
    let observations = [];
    const keys = new Set();

    function prune(now) {
        const cutoff = now - windowMs;
        observations = observations.filter(item => item.timestamp >= cutoff);
        keys.clear();
        observations.forEach(item => keys.add(item.key));
    }

    return {
        record(rows, receivedAt = Date.now()) {
            if (!Array.isArray(rows)) throw new Error("Expected normalized file activity rows.");
            if (!Number.isFinite(receivedAt)) throw new Error("Expected a valid observation timestamp.");

            const firstWindow = rows.find(row => row.windowEndUtc || row.windowStartUtc);
            const start = timestamp(firstWindow?.windowStartUtc);
            const end = timestamp(firstWindow?.windowEndUtc);
            const observed = rows.map(row => timestamp(row.observedAt)).find(value => value !== null);
            const observedAt = end ?? observed ?? receivedAt;
            const key = start !== null && end !== null
                ? `window:${start}:${end}`
                : rows.length ? `observed:${observedAt}` : `empty:${receivedAt}`;

            prune(receivedAt);
            if (keys.has(key)) return false;

            observations.push({ timestamp: observedAt, receivedAt, key, rows: rows.slice() });
            observations.sort((a, b) => a.timestamp - b.timestamp);
            keys.add(key);
            prune(receivedAt);
            return true;
        },

        getObservations(now = Date.now()) {
            prune(now);
            return observations.slice();
        },

        clear() {
            observations = [];
            keys.clear();
        }
    };
}

/** Build chart points directly from the byte/op totals in each API window. */
export function buildFileActivityHistory(observations) {
    return observations.map(observation => {
        const rows = observation.rows;
        const readRates = rows.map(row => rateFor(row, "readBytes"));
        const writeRates = rows.map(row => rateFor(row, "writeBytes"));
        const readOperationRates = rows.map(row => rateFor(row, "readOps"));
        const writeOperationRates = rows.map(row => rateFor(row, "writeOps"));
        const sum = values => values.length && values.every(value => value !== null)
            ? values.reduce((total, value) => total + value, 0)
            : null;
        const readBytesPerSecond = sum(readRates);
        const writeBytesPerSecond = sum(writeRates);
        const readOpsPerSecond = sum(readOperationRates);
        const writeOpsPerSecond = sum(writeOperationRates);

        return {
            timestamp: observation.timestamp,
            readBytesPerSecond,
            writeBytesPerSecond,
            totalBytesPerSecond: readBytesPerSecond !== null && writeBytesPerSecond !== null
                ? readBytesPerSecond + writeBytesPerSecond
                : null,
            readOpsPerSecond,
            writeOpsPerSecond
        };
    });
}

/** Rank files by average observed throughput; missing samples are not zero. */
export function rankFileActivity(observations, limit = 10) {
    const files = new Map();

    for (const observation of observations) {
        const seenThisObservation = new Set();
        for (const row of observation.rows) {
            const key = row.fileId || row.path;
            if (!key || seenThisObservation.has(key)) continue;
            seenThisObservation.add(key);

            const read = rateFor(row, "readBytes");
            const write = rateFor(row, "writeBytes");
            const readOps = rateFor(row, "readOps");
            const writeOps = rateFor(row, "writeOps");
            const entry = files.get(key) ?? {
                key,
                path: row.path || row.name || key,
                name: row.name || null,
                throughputTotal: 0,
                throughputSamples: 0,
                operationRateTotal: 0,
                operationRateSamples: 0
            };

            const knownByteRates = [read, write].filter(value => value !== null);
            if (knownByteRates.length) {
                entry.throughputTotal += knownByteRates.reduce((total, value) => total + value, 0);
                entry.throughputSamples += 1;
            }
            const knownOperationRates = [readOps, writeOps].filter(value => value !== null);
            if (knownOperationRates.length) {
                entry.operationRateTotal += knownOperationRates.reduce((total, value) => total + value, 0);
                entry.operationRateSamples += 1;
            }
            files.set(key, entry);
        }
    }

    return [...files.values()]
        .map(file => ({
            ...file,
            averageBytesPerSecond: file.throughputSamples
                ? file.throughputTotal / file.throughputSamples
                : null,
            averageOperationsPerSecond: file.operationRateSamples
                ? file.operationRateTotal / file.operationRateSamples
                : null
        }))
        .sort((a, b) => (b.averageBytesPerSecond ?? -1) - (a.averageBytesPerSecond ?? -1))
        .slice(0, limit);
}
