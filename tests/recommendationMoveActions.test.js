import test from "node:test";
import assert from "node:assert/strict";
import {
    createRecommendationMoveController,
    isMoveErrorResult,
    resolveRecommendationMove
} from "../frontend/js/recommendationMoveActions.js";

const recommendation = (id, overrides = {}) => ({
    recommendation_id: id,
    mode: "raid0",
    action: "move",
    file_id: "42",
    source_device_id: "disk-a",
    target_device_id: "disk-b",
    ...overrides
});

test("move details resolve the matching source path and recommended destination device", () => {
    const details = resolveRecommendationMove(
        recommendation("rec-1"),
        [
            { fileId: "42", deviceId: "disk-other", path: "/other/file.txt", name: "file.txt" },
            { fileId: "42", deviceId: "disk-a", path: "/pool/file.txt", name: "file.txt" }
        ],
        [{ device_id: "disk-b", display_name: "Fast SSD" }],
        true
    );

    assert.equal(details.available, true);
    assert.equal(details.file.path, "/pool/file.txt");
    assert.equal(details.targetDevice.display_name, "Fast SSD");
});

test("move details are unavailable without capability, source path, or target drive", () => {
    const rec = recommendation("rec-2");
    const file = [{ fileId: "42", deviceId: "disk-a", path: "/pool/file.txt" }];
    const device = [{ device_id: "disk-b" }];

    assert.equal(resolveRecommendationMove(rec, file, device, false).available, false);
    assert.match(resolveRecommendationMove(rec, [], device, true).reason, /source path/i);
    assert.match(resolveRecommendationMove(rec, file, [], true).reason, /destination drive/i);
    assert.equal(resolveRecommendationMove(recommendation("rec-3", { action: "none" }), file, device, true).available, false);
});

test("move controller polls concurrent actions independently and only confirms terminal outcomes", async () => {
    const requests = [];
    const statusCalls = new Map();
    const toasts = [];
    const timers = [];
    let nextTimer = 0;
    const controller = createRecommendationMoveController({
        execute: async recommendationId => {
            requests.push(recommendationId);
            return `action-${recommendationId}`;
        },
        getStatus: async actionId => {
            const calls = (statusCalls.get(actionId) ?? 0) + 1;
            statusCalls.set(actionId, calls);
            if (actionId === "action-rec-a" && calls === 1) {
                return { progress: 0.4, is_running: true, result: null };
            }
            if (actionId === "action-rec-a") {
                return { progress: 1, is_running: false, result: "/ssd/file.txt" };
            }
            return { progress: 0, is_running: false, result: "FILE_NOT_FOUND" };
        },
        onToast: toast => toasts.push(toast),
        schedule: (callback, delay) => {
            const timer = { id: ++nextTimer, callback, delay };
            timers.push(timer);
            return timer.id;
        },
        cancel: id => {
            const index = timers.findIndex(timer => timer.id === id);
            if (index !== -1) timers.splice(index, 1);
        }
    });
    const settle = async () => { await Promise.resolve(); await Promise.resolve(); };

    await Promise.all([
        controller.start(recommendation("rec-a")),
        controller.start(recommendation("rec-b"))
    ]);
    await settle();

    assert.deepEqual(requests.sort(), ["rec-a", "rec-b"]);
    assert.equal(controller.getState("rec-a").status, "running");
    assert.equal(controller.getState("rec-a").progress, 0.4);
    assert.equal(controller.getState("rec-b").status, "failed");
    assert.equal(controller.getState("rec-b").retryAllowed, true);
    assert.ok(toasts.some(toast => toast.type === "failed" && toast.recommendation.recommendation_id === "rec-b"));
    assert.equal(toasts.some(toast => toast.type === "completed"), false);
    assert.equal(await controller.start(recommendation("rec-a")), false);

    const timer = timers.find(item => item.delay === 1000);
    timer.callback();
    await settle();
    assert.equal(controller.getState("rec-a").status, "completed");
    assert.equal(controller.getState("rec-a").result, "/ssd/file.txt");
    assert.equal(toasts.filter(toast => toast.type === "completed").length, 1);
    controller.dispose();
});

test("a move request without an action ID stays unconfirmed and cannot be auto-retried", async () => {
    let attempts = 0;
    const notifications = [];
    const controller = createRecommendationMoveController({
        execute: async () => {
            attempts += 1;
            throw new Error("Network timeout");
        },
        getStatus: async () => ({ is_running: true }),
        onToast: notification => notifications.push(notification)
    });
    const rec = recommendation("rec-unknown");

    assert.equal(await controller.start(rec), false);
    assert.equal(controller.getState("rec-unknown").status, "unknown");
    assert.equal(controller.getState("rec-unknown").retryAllowed, false);
    assert.equal(await controller.start(rec), false);
    assert.equal(attempts, 1);
    assert.equal(notifications[0].type, "unknown");
    controller.dispose();
});

test("error results are distinct from completed destination paths", () => {
    assert.equal(isMoveErrorResult("FILE_NOT_FOUND"), true);
    assert.equal(isMoveErrorResult("/mnt/ssd/report.pdf"), false);
});
