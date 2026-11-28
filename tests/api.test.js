import test from "node:test";
import assert from "node:assert/strict";
import {
    createFileSubscription,
    deleteFileSubscription,
    executeFileMove,
    executeRecommendedFileMove,
    getCapabilities,
    getDevices,
    getFileActionStatus,
    getFileSubscriptions,
    getLatestFileActivity,
    getLatestMetrics,
    getLatestProcesses,
    getProcessHistory,
    getRecommendations,
    refreshRecommendations,
    setMockDataEnabled
} from "../frontend/js/api.js";

test("frontend API calls match the implemented Flask request contracts", async () => {
    const originalFetch = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, options = {}) => {
        calls.push({ url, options });
        let data = [];
        if (url === "/api/v1/actions/execute") data = "move-1";
        if (url === "/api/v1/actions/move-1") {
            data = { progress: 0.5, is_running: true, result: null };
        }
        return {
            ok: true,
            status: 200,
            json: async () => ({ status: "success", data, error: null })
        };
    };

    try {
        setMockDataEnabled(false);
        await getDevices();
        await getLatestMetrics();
        await getLatestProcesses();
        await getProcessHistory({
            process_instance_id: "42_started-at",
            start_utc: "2026-11-25T10:00:00.000Z",
            end_utc: "2026-11-25T10:05:00.000Z",
            bucket_seconds: 60
        });
        await getRecommendations("ssd_caching");
        await refreshRecommendations("raid0");
        await getCapabilities();
        await getLatestFileActivity();
        await getFileSubscriptions();
        await createFileSubscription("/data/file.txt");
        await deleteFileSubscription("/data/file.txt");
        await executeFileMove("/pool/file.txt", "/mnt/ssd");
        await executeRecommendedFileMove("rec-raid0-001");
        await getFileActionStatus("move-1");

        assert.deepEqual(calls.map(call => [call.options.method ?? "GET", call.url]), [
            ["GET", "/api/v1/devices"],
            ["GET", "/api/v1/metrics/latest"],
            ["GET", "/api/v1/processes/latest"],
            ["GET", "/api/v1/processes/history?process_instance_id=42_started-at&start_utc=2026-11-25T10%3A00%3A00.000Z&end_utc=2026-11-25T10%3A05%3A00.000Z&bucket_seconds=60"],
            ["GET", "/api/v1/recommendations?mode=ssd_caching"],
            ["POST", "/api/v1/recommendations/refresh?mode=raid0"],
            ["GET", "/api/v1/capabilities"],
            ["GET", "/api/v1/files/activity/latest"],
            ["GET", "/api/v1/files/subscriptions"],
            ["POST", "/api/v1/files/subscriptions"],
            ["DELETE", "/api/v1/files/subscriptions"],
            ["POST", "/api/v1/actions/execute"],
            ["POST", "/api/v1/actions/execute"],
            ["GET", "/api/v1/actions/move-1"]
        ]);

        assert.deepEqual(JSON.parse(calls[9].options.body), { path: "/data/file.txt" });
        assert.deepEqual(JSON.parse(calls[10].options.body), { path: "/data/file.txt" });
        assert.deepEqual(JSON.parse(calls[11].options.body), {
            file_path: "/pool/file.txt",
            destination_mount: "/mnt/ssd"
        });
        assert.deepEqual(JSON.parse(calls[12].options.body), {
            recommendation_id: "rec-raid0-001"
        });
        for (const index of [9, 10, 11, 12]) {
            assert.equal(calls[index].options.headers["Content-Type"], "application/json");
        }
    } finally {
        globalThis.fetch = originalFetch;
        setMockDataEnabled(false);
    }
});

test("API errors preserve backend codes and messages", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => ({
        ok: false,
        status: 400,
        json: async () => ({
            status: "error",
            data: null,
            error: { code: "INVALID_REQUEST", message: "Missing parameter" }
        })
    });

    try {
        await assert.rejects(getDevices(), /INVALID_REQUEST: Missing parameter \(HTTP 400\)/);
    } finally {
        globalThis.fetch = originalFetch;
    }
});
