// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import {
    mockDevices,
    getMockMetrics,
    getMockProcesses,
    getMockProcessHistory
} from "./mockData.js";

// Flask backend address from backend/main.py.
const API_BASE_URL = "";

// Keep true while testing the frontend with mock device/process data.
// Recommendations always use the real Flask backend.
const USE_MOCK_DATA = false;

/* SHARED API REQUEST FUNCTION */

async function getJson(path, options = {}) {
    const url = path.startsWith("http")
        ? path
        : `${API_BASE_URL}${path}`;

    const response = await fetch(url, options);

    // Try to extract the backend's error message if the request failed.
    if (!response.ok) {
        let message = `HTTP error ${response.status}`;

        try {
            const errorResult = await response.json();

            if (errorResult.error) {
                message += `: ${JSON.stringify(errorResult.error)}`;
            }
        } catch {
            // The response may not contain JSON.
        }

        throw new Error(message);
    }

    const result = await response.json();

    if (result.status !== "success") {
        const message = result.error
            ? JSON.stringify(result.error)
            : "The API returned an error.";

        throw new Error(message);
    }

    return result.data;
}

/* DEVICES */

export async function getDevices() {
    if (USE_MOCK_DATA) {
        return mockDevices;
    }

    return getJson("/api/v1/devices");
}

/* DISK METRICS */

export async function getLatestMetrics() {
    if (USE_MOCK_DATA) {
        return getMockMetrics();
    }

    return getJson("/api/v1/metrics/latest");
}

/* PROCESS INFORMATION */

export async function getLatestProcesses() {
    if (USE_MOCK_DATA) {
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

export async function refreshRecommendations() {
    return getJson("/api/v1/recommendations/refresh", {
        method: "POST"
    });
}

/* BACKEND CAPABILITIES */

export async function getCapabilities() {
    return getJson("/api/v1/capabilities");
}
