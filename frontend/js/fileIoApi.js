// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { getCapabilities } from "./api.js";

/*
 * The documented FileActivity record is an OS/core data shape, not a live HTTP
 * contract. Flask currently exposes no file activity or file history route.
 * Do not add a guessed URL here; wire the API call once the route is agreed.
 *
 * Expected future API envelope: { status: "success", data: FileActivity[] }
 * FileActivity fields follow docs/api-contracts.md §02.1.
 */
export async function getFileIoAvailability() {
    const capabilities = await getCapabilities();
    return {
        reportedCapability: capabilities && Object.hasOwn(capabilities, "file_access_metrics")
            ? capabilities.file_access_metrics
            : null,
        activityEndpointAvailable: false
    };
}

const numeric = value => typeof value === "number" && Number.isFinite(value) && value >= 0
    ? value
    : null;

function windowSeconds(row) {
    const start = Date.parse(row?.window_start_utc);
    const end = Date.parse(row?.window_end_utc);
    return Number.isFinite(start) && Number.isFinite(end) && end > start
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

/** Convert documented FileActivity window records into display-ready rows. */
export function normalizeFileActivity(records) {
    if (!Array.isArray(records)) {
        throw new Error("Expected file activity data to be an array of FileActivity records.");
    }

    return records.map(record => {
        const row = record && typeof record === "object" ? record : {};
        const seconds = windowSeconds(row);
        const readBytes = numeric(row?.read_bytes);
        const writeBytes = numeric(row?.write_bytes);
        const readOps = numeric(row?.read_ops);
        const writeOps = numeric(row?.write_ops);
        const readBytesPerSec = rate(readBytes, seconds);
        const writeBytesPerSec = rate(writeBytes, seconds);

        return {
            fileId: typeof row?.file_id === "string" ? row.file_id : null,
            path: typeof row?.path === "string" ? row.path : null,
            name: fileName(row?.path),
            deviceId: row?.device_id == null ? null : String(row.device_id),
            source: typeof row?.source === "string" ? row.source : null,
            windowStartUtc: row?.window_start_utc ?? null,
            windowEndUtc: row?.window_end_utc ?? null,
            durationSeconds: seconds,
            readBytes,
            writeBytes,
            readOps,
            writeOps,
            fileSizeBytes: numeric(row?.file_size_bytes),
            readBytesPerSec,
            writeBytesPerSec,
            readOpsPerSec: rate(readOps, seconds),
            writeOpsPerSec: rate(writeOps, seconds),
            totalBytesPerSec: readBytesPerSec !== null && writeBytesPerSec !== null
                ? readBytesPerSec + writeBytesPerSec
                : null,
            lastActivity: Number.isFinite(Date.parse(row?.window_end_utc))
                ? row.window_end_utc
                : null
        };
    });
}
