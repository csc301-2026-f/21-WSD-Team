// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
function parseTimestamp(value) {
    if (typeof value !== "string" || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
    const timestamp = Date.parse(value);
    return Number.isFinite(timestamp) ? timestamp : null;
}

function windowSeconds(row) {
    const start = parseTimestamp(row?.window_start_utc);
    const end = parseTimestamp(row?.window_end_utc);
    return start !== null && end !== null && end > start
        ? (end - start) / 1000
        : null;
}

function rate(count, seconds) {
    return count !== null && seconds !== null && seconds > 0 ? count / seconds : null;
}

function fileName(path) {
    if (typeof path !== "string" || !path) return null;
    return path.split(/[\\/]/).filter(Boolean).at(-1) || path;
}

function firstValue(...values) {
    return values.find(value => value !== undefined && value !== null);
}

function numericField(...values) {
    for (const value of values) {
        if (typeof value === "number" && Number.isFinite(value) && value >= 0) return value;
    }
    return null;
}

function stringField(value) {
    return value === undefined || value === null || value === "" ? null : String(value);
}

const isKnownNumber = value => typeof value === "number" && Number.isFinite(value) && value >= 0;

function sumKnown(rows, field) {
    if (!rows.length) return null;
    const values = rows.map(row => row[field]);
    return values.every(isKnownNumber) ? values.reduce((sum, value) => sum + value, 0) : null;
}

function totalBytes(row) {
    return isKnownNumber(row.readBytes) && isKnownNumber(row.writeBytes)
        ? row.readBytes + row.writeBytes
        : null;
}

/** Aggregate only values known for every returned row; null remains unavailable. */
export function summarizeFileActivity(rows) {
    if (!Array.isArray(rows)) throw new Error("Expected normalized file activity rows.");
    const mostActiveFile = rows.length && rows.every(row => totalBytes(row) !== null)
        ? [...rows].sort((a, b) => totalBytes(b) - totalBytes(a))[0]
        : null;
    return {
        fileCount: rows.length,
        totalReadBytes: sumKnown(rows, "readBytes"),
        totalWriteBytes: sumKnown(rows, "writeBytes"),
        totalReadOps: sumKnown(rows, "readOps"),
        totalWriteOps: sumKnown(rows, "writeOps"),
        mostActiveFile
    };
}

/** Filter and sort normalized rows for the File I/O table. */
export function filterAndSortFileActivity(rows, { query = "", activity = "all", sort = "total_bytes" } = {}) {
    const normalizedQuery = query.trim().toLowerCase();
    const filtered = rows.filter(row => {
        const matchesQuery = !normalizedQuery || `${row.path ?? ""} ${row.name ?? ""}`.toLowerCase().includes(normalizedQuery);
        const hasRead = (isKnownNumber(row.readBytes) && row.readBytes > 0) || (isKnownNumber(row.readOps) && row.readOps > 0);
        const hasWrite = (isKnownNumber(row.writeBytes) && row.writeBytes > 0) || (isKnownNumber(row.writeOps) && row.writeOps > 0);
        const matchesActivity = activity === "all" || (activity === "read" ? hasRead : hasWrite);
        return matchesQuery && matchesActivity;
    });
    const valueFor = row => ({
        total_bytes: totalBytes(row),
        read_bytes: row.readBytes,
        write_bytes: row.writeBytes,
        total_ops: isKnownNumber(row.readOps) && isKnownNumber(row.writeOps) ? row.readOps + row.writeOps : null,
        read_ops: row.readOps,
        write_ops: row.writeOps,
        name: row.name ?? "",
        path: row.path ?? ""
    })[sort];

    return filtered.sort((a, b) => {
        const left = valueFor(a), right = valueFor(b);
        if (typeof left === "string") return left.localeCompare(right);
        if (left == null) return right == null ? 0 : 1;
        if (right == null) return -1;
        return right - left;
    });
}

/** Adapt the Windows FileActivity shape and compatible Linux file metrics. */
export function normalizeFileActivity(records) {
    if (!Array.isArray(records)) {
        throw new Error("Expected file activity data to be an array of FileActivity records.");
    }

    return records.map(record => {
        const row = record && typeof record === "object" ? record : {};
        const file = row.file && typeof row.file === "object" ? row.file : {};
        const path = stringField(firstValue(row.path, row.absolute_path, file.path, file.absolute_path));
        const windowStartUtc = firstValue(row.window_start_utc, row.window_start, row.start_utc);
        const windowEndUtc = firstValue(row.window_end_utc, row.window_end, row.end_utc);
        const normalizedWindow = { window_start_utc: windowStartUtc, window_end_utc: windowEndUtc };
        const seconds = windowSeconds(normalizedWindow);
        const readBytes = numericField(row.read_bytes, row.read_completed_bytes);
        const writeBytes = numericField(row.write_bytes, row.write_completed_bytes);
        const readOps = numericField(row.read_ops, row.read_success_ops);
        const writeOps = numericField(row.write_ops, row.write_success_ops);
        const readBytesPerSec = rate(readBytes, seconds);
        const writeBytesPerSec = rate(writeBytes, seconds);
        const observedAt = firstValue(row.timestamp_utc, row.timestamp);
        const rawFileId = firstValue(row.file_id, row.fileId, file.file_id, file.inode);
        const rawDeviceId = firstValue(row.device_id, row.deviceId, file.device_id, file.device);

        return {
            hostId: stringField(row.host_id),
            fileId: stringField(rawFileId),
            path,
            name: fileName(path),
            deviceId: stringField(rawDeviceId),
            source: stringField(firstValue(row.source, row.collector)),
            windowStartUtc: windowStartUtc ?? null,
            windowEndUtc: windowEndUtc ?? null,
            observedAt: observedAt ?? null,
            durationSeconds: seconds,
            readBytes,
            writeBytes,
            readOps,
            writeOps,
            fileSizeBytes: numericField(row.file_size_bytes, row.size_bytes, row.file_size, file.size_bytes),
            readBytesPerSec,
            writeBytesPerSec,
            readOpsPerSec: rate(readOps, seconds),
            writeOpsPerSec: rate(writeOps, seconds),
            totalBytesPerSec: readBytesPerSec !== null && writeBytesPerSec !== null
                ? readBytesPerSec + writeBytesPerSec
                : null,
            lastActivity: parseTimestamp(windowEndUtc) !== null
                ? windowEndUtc
                : parseTimestamp(observedAt) !== null ? observedAt : null
        };
    });
}
