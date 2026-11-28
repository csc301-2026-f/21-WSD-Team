// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only

export function resolveRecommendationMove(recommendation, fileActivity, devices, fileMoveAvailable) {
    if (recommendation?.mode !== "raid0" || recommendation?.action !== "move") {
        return { available: false, reason: "This recommendation does not describe a file move." };
    }
    if (typeof recommendation.recommendation_id !== "string" || !recommendation.recommendation_id) {
        return { available: false, reason: "The recommendation has no action identifier." };
    }
    if (fileMoveAvailable !== true) {
        return {
            available: false,
            reason: fileMoveAvailable === false
                ? "The backend reports file movement is unavailable."
                : "Backend file-move support could not be confirmed."
        };
    }

    const fileId = recommendation.file_id == null ? "" : String(recommendation.file_id);
    const matches = Array.isArray(fileActivity)
        ? fileActivity.filter(file => file.fileId === fileId && file.path)
        : [];
    const file = recommendation.source_device_id == null
        ? null
        : matches.find(item => item.deviceId === String(recommendation.source_device_id)) ?? null;
    if (!file || !isAbsoluteFilePath(file.path)) {
        return { available: false, reason: "A valid absolute source path is not present in current FileActivity data." };
    }

    const targetId = recommendation.target_device_id == null
        ? ""
        : String(recommendation.target_device_id);
    const targetDevice = Array.isArray(devices)
        ? devices.find(device => String(device.device_id) === targetId)
        : null;
    if (!targetDevice) {
        return { available: false, reason: "The recommended destination drive is not present in device data." };
    }

    return { available: true, file, targetDevice };
}

export function isMoveErrorResult(result) {
    return typeof result === "string" && /^[A-Z][A-Z0-9_]+$/.test(result);
}

function isAbsoluteFilePath(path) {
    return typeof path === "string" && (
        path.startsWith("/") ||
        /^[A-Za-z]:[\\/]/.test(path) ||
        path.startsWith("\\\\")
    );
}

/** Tracks independent recommendation moves and polls each accepted action once at a time. */
export function createRecommendationMoveController({
    execute,
    getStatus,
    onChange = () => {},
    onToast = () => {},
    schedule = (callback, delay) => window.setTimeout(callback, delay),
    cancel = timer => window.clearTimeout(timer),
    pollIntervalMs = 1000,
    retryIntervalMs = 4000,
    maxStatusCheckFailures = 8
}) {
    const states = new Map();
    let paused = false;
    let disposed = false;

    function publish(recommendationId) {
        const state = states.get(recommendationId);
        if (state) onChange(recommendationId, { ...state });
    }

    function clearTimer(state) {
        if (state.timer !== null) {
            cancel(state.timer);
            state.timer = null;
        }
    }

    function schedulePoll(recommendationId, delay) {
        const state = states.get(recommendationId);
        if (!state || paused || disposed || state.status !== "running" || state.polling) return;
        clearTimer(state);
        state.timer = schedule(() => {
            state.timer = null;
            void poll(recommendationId, state.actionId);
        }, delay);
    }

    async function poll(recommendationId, actionId) {
        const state = states.get(recommendationId);
        if (!state || paused || disposed || state.actionId !== actionId || state.polling) return;
        state.polling = true;
        try {
            const action = await getStatus(actionId);
            if (!action || typeof action !== "object" || typeof action.is_running !== "boolean") {
                throw new Error("The action status response is missing is_running.");
            }

            state.progress = typeof action.progress === "number" && Number.isFinite(action.progress)
                ? action.progress
                : null;
            state.statusError = null;
            state.statusCheckFailures = 0;
            if (action.is_running) {
                publish(recommendationId);
                return;
            }

            state.result = typeof action.result === "string" ? action.result : null;
            state.status = state.result && !isMoveErrorResult(state.result) ? "completed" : "failed";
            if (state.status === "completed") {
                onToast({ type: "completed", recommendation: state.recommendation, result: state.result });
            } else {
                state.error = state.result || "The backend ended the action without a result.";
                state.retryAllowed = Boolean(state.result && isMoveErrorResult(state.result));
                onToast({ type: "failed", recommendation: state.recommendation, message: state.error });
            }
            publish(recommendationId);
        } catch (error) {
            state.statusError = error instanceof Error ? error.message : String(error);
            state.statusCheckFailures += 1;
            if (state.statusCheckFailures >= maxStatusCheckFailures) {
                state.status = "unknown";
                state.error = "Could not confirm the move status after repeated checks.";
                onToast({ type: "unknown", recommendation: state.recommendation, message: state.error });
            }
            publish(recommendationId);
        } finally {
            state.polling = false;
            if (state.status === "running") {
                schedulePoll(recommendationId, state.statusError ? retryIntervalMs : pollIntervalMs);
            }
        }
    }

    async function start(recommendation) {
        const recommendationId = recommendation?.recommendation_id;
        if (typeof recommendationId !== "string" || !recommendationId || disposed) return false;

        const previous = states.get(recommendationId);
        if (previous && ["starting", "running", "completed", "unknown"].includes(previous.status)) return false;

        const state = {
            recommendation,
            status: "starting",
            actionId: null,
            progress: null,
            result: null,
            error: null,
            retryAllowed: false,
            statusCheckFailures: 0,
            statusError: null,
            polling: false,
            timer: null
        };
        states.set(recommendationId, state);
        publish(recommendationId);

        try {
            const actionId = await execute(recommendationId);
            if (typeof actionId !== "string" || !actionId) {
                throw new Error("The backend did not return a move action ID.");
            }
            state.actionId = actionId;
            state.status = "running";
            onToast({ type: "started", recommendation, actionId });
            publish(recommendationId);
            void poll(recommendationId, actionId);
            return actionId;
        } catch (error) {
            state.status = "unknown";
            const detail = error instanceof Error ? error.message : String(error);
            state.error = `No action ID was returned. The move may have started; verify the file location before retrying. ${detail}`;
            onToast({ type: "unknown", recommendation, message: state.error });
            publish(recommendationId);
            return false;
        }
    }

    return {
        getState(recommendationId) {
            const state = states.get(recommendationId);
            return state ? { ...state } : null;
        },
        start,
        pause() {
            paused = true;
            for (const state of states.values()) clearTimer(state);
        },
        resume() {
            if (disposed) return;
            paused = false;
            for (const [recommendationId, state] of states) {
                if (state.status === "running" && !state.polling) {
                    void poll(recommendationId, state.actionId);
                }
            }
        },
        dispose() {
            disposed = true;
            for (const state of states.values()) clearTimer(state);
        }
    };
}
