import {
    mockDevices,
    getMockMetrics,
    getMockProcesses,
    getMockProcessHistory
} from "./mockData.js";

// TRUE ONLY FOR TESTING
const USE_MOCK_DATA = true;

async function getJson(path, options = {}) {
    const response = await fetch(path, options);

    if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
    }

    const result = await response.json();

    if (result.status !== "success") {
        throw new Error("The API returned an error");
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
    host_id,
    pid,
    start_time_utc,
    start_utc,
    end_utc,
    bucket_seconds
}) {
    if (USE_MOCK_DATA) {
        return getMockProcessHistory({
            host_id,
            pid,
            start_time_utc,
            start_utc,
            end_utc,
            bucket_seconds
        });
    }

    const params = new URLSearchParams({
        host_id,
        pid: String(pid),
        start_time_utc,
        start_utc,
        end_utc
    });

    if (bucket_seconds != null) {
        params.set("bucket_seconds", String(bucket_seconds));
    }

    return getJson(`/api/v1/processes/history?${params.toString()}`);
}

/* RECOMMENDATIONS */

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

export async function refreshRecommendations() {
    return getJson("/api/v1/recommendations/refresh", {
        method: "POST"
    });
}
