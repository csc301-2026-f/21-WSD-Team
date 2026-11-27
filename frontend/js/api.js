// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import {
    mockDevices,
    getMockMetrics,
    getMockProcesses,
    getMockProcessHistory,
    getMockFileActivity
} from "./mockData.js";

// Flask backend address from backend/main.py.
const API_BASE_URL = "";

// Default data mode for device, process, and file activity APIs. The File I/O
// page can switch this shared API setting for its current page session.
// Recommendations always use the real Flask backend.
const USE_MOCK_DATA = false;
let mockDataEnabled = USE_MOCK_DATA;

export function isMockDataEnabled() {
    return mockDataEnabled;
}

export function setMockDataEnabled(enabled) {
    mockDataEnabled = Boolean(enabled);
}

/* SHARED API REQUEST FUNCTION */

async function getJson(path, options = {}) {
    const url = path.startsWith("http")
        ? path
        : `${API_BASE_URL}${path}`;

    const response = await fetch(url, options);
    let result;

    try {
        result = await response.json();
    } catch {
        const detail = response.ok
            ? "The API response was not valid JSON."
            : `HTTP error ${response.status} with a non-JSON response.`;
        throw new Error(detail);
    }

    if (!result || typeof result !== "object" || Array.isArray(result)) {
        throw new Error("The API returned an invalid response envelope.");
    }

    if (!response.ok || result.status !== "success") {
        const apiError = result.error;
        const code = typeof apiError?.code === "string" ? apiError.code : null;
        const message = typeof apiError?.message === "string"
            ? apiError.message
            : `The API returned ${result.status || "an invalid status"}.`;
        const status = response.ok ? "" : ` (HTTP ${response.status})`;
        throw new Error(`${code ? `${code}: ` : ""}${message}${status}`);
    }

    if (!Object.hasOwn(result, "data")) {
        throw new Error("The API success response did not include data.");
    }

    return result.data;
}

function withActionTimeout(options = {}) {
    if (options.signal || typeof AbortSignal === "undefined" || typeof AbortSignal.timeout !== "function") {
        return options;
    }
    return { ...options, signal: AbortSignal.timeout(15_000) };
}

/* DEVICES */

export async function getDevices() {
    if (isMockDataEnabled()) {
        return mockDevices;
    }

    return getJson("/api/v1/devices");
}

/* DISK METRICS */

export async function getLatestMetrics() {
    if (isMockDataEnabled()) {
        return getMockMetrics();
    }

    return getJson("/api/v1/metrics/latest");
}

/* PROCESS INFORMATION */

export async function getLatestProcesses() {
    if (isMockDataEnabled()) {
        return getMockProcesses();
    }

    return getJson("/api/v1/processes/latest");
}

/* PROCESS HISTORY */

export async function getProcessHistory({
    process_instance_id,
    start_utc,
    end_utc,
    bucket_seconds
}) {
    if (isMockDataEnabled()) {
        return getMockProcessHistory({
            process_instance_id,
            start_utc,
            end_utc,
            bucket_seconds
        });
    }

    const params = new URLSearchParams({
        process_instance_id,
        start_utc,
        end_utc
    });

    if (bucket_seconds != null) {
        params.set("bucket_seconds", String(bucket_seconds));
    }

    return getJson(
        `/api/v1/processes/history?${params.toString()}`
    );
}

/* RECOMMENDATIONS */

/*
 * Recommendations always use Flask.
 * They are not affected by USE_MOCK_DATA.
 */

export async function getRecommendations(mode) {
    const params = new URLSearchParams();

    if (mode) {
        params.set("mode", mode);
    }

    const query = params.toString();

    const path = query
        ? `/api/v1/recommendations?${query}`
        : "/api/v1/recommendations";

    return getJson(path);
}

/* REFRESH RECOMMENDATIONS */

/*
 * Calls the backend algorithm and returns its generated recommendations.
 * This does not mean that any recommended file operation was executed.
 */

export async function refreshRecommendations(mode) {
    const params = new URLSearchParams();

    if (mode) {
        params.set("mode", mode);
    }

    const query = params.toString();
    const path = query
        ? `/api/v1/recommendations/refresh?${query}`
        : "/api/v1/recommendations/refresh";

    return getJson(path, {
        method: "POST"
    });
}

/* BACKEND CAPABILITIES */

export async function getCapabilities() {
    return getJson("/api/v1/capabilities");
}

/* LATEST FILE ACTIVITY */

export async function getLatestFileActivity() {
    if (isMockDataEnabled()) {
        return getMockFileActivity();
    }

    return getJson("/api/v1/files/activity/latest");
}

/* FILE AND FOLDER SUBSCRIPTIONS */

const subscriptionPath = "/api/v1/files/subscriptions";

export async function getFileSubscriptions() {
    return getJson(subscriptionPath);
}

export async function createFileSubscription(path) {
    return getJson(subscriptionPath, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path })
    });
}

export async function deleteFileSubscription(path) {
    return getJson(subscriptionPath, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path })
    });
}

/* MERGERFS FILE MOVE ACTIONS */

export async function executeFileMove(filePath, destinationMount) {
    return getJson("/api/v1/actions/execute", withActionTimeout({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            file_path: filePath,
            destination_mount: destinationMount
        })
    }));
}

export async function executeRecommendedFileMove(recommendationId) {
    return getJson("/api/v1/actions/execute", withActionTimeout({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recommendation_id: recommendationId })
    }));
}

export async function getFileActionStatus(actionId) {
    return getJson(`/api/v1/actions/${encodeURIComponent(actionId)}`, withActionTimeout());
}
