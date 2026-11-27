// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only

import {
    executeRecommendedFileMove,
    getCapabilities,
    getDevices,
    getFileActionStatus,
    getLatestFileActivity,
    getRecommendations,
    refreshRecommendations
} from "./api.js";
import { normalizeFileActivity } from "./fileIoApi.js";
import {
    createRecommendationMoveController,
    isMoveErrorResult,
    resolveRecommendationMove
} from "./recommendationMoveActions.js";

const container = document.getElementById("recommendations-container");
const statusElement = document.getElementById("recommendations-status");
const refreshButton = document.getElementById(
    "refresh-recommendations-button"
);
const moveDemoButton = document.getElementById("toggle-move-demo-button");

let isRefreshing = false;
let currentRecommendations = [];
let currentFileActivity = [];
let currentDevices = [];
let fileMoveCapability = null;
let moveController = null;
let pendingMoveRecommendation = null;
let pendingMoveIsDemo = false;
let showMoveDemo = false;
let demoMovePreviewed = false;
const movementToasts = new Map();
const filterInput = document.getElementById("recommendation-filter");
const sortSelect = document.getElementById("recommendation-sort");
const modeSelect = document.getElementById("recommendation-mode");
const moveDialog = document.getElementById("move-confirmation-dialog");
const moveDialogTitle = document.getElementById("move-confirmation-title");
const moveDialogIntro = document.getElementById("move-confirmation-intro");
const moveDialogWarning = document.getElementById("move-confirmation-warning");
const moveDialogName = document.getElementById("move-confirmation-name");
const moveDialogPath = document.getElementById("move-confirmation-path");
const moveDialogDestination = document.getElementById("move-confirmation-destination");
const cancelMoveButton = document.getElementById("cancel-move-button");
const confirmMoveButton = document.getElementById("confirm-move-button");
const movementToastStack = document.getElementById("movement-toast-stack");
const demoMoveRecommendation = {
    recommendation_id: "demo-preview",
    mode: "raid0",
    action: "move",
    file_id: "demo-report-001",
    source_device_id: "Demo HDD",
    target_device_id: "Demo SSD",
    reason: "Sample recommendation for previewing the file-move controls.",
    created_at_utc: "2026-11-26T12:00:00Z",
    requires_approval: true,
    estimated_benefit: null,
    constraints: ["Demo preview only; no real file operation is available."],
    demoPreview: true,
    demoFileName: "quarterly-report.pdf",
    demoFilePath: "/demo/pool/reports/quarterly-report.pdf",
    demoDestinationLabel: "Demo SSD (sample drive)"
};

function updateRefreshAvailability() {
    refreshButton.disabled = isRefreshing;
    const mode = modeSelect?.value;
    const label = mode === "ssd_caching"
        ? "SSD Caching"
        : "RAID 0 / file-level pooling";
    refreshButton.title = `Generate ${label} recommendations from current backend data.`;
}

/* ELEMENT CREATION */

function createElement(tag, className, text) {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined && text !== null) {
        element.textContent = String(text);
    }

    return element;
}

function addDetail(card, label, value) {
    const row = createElement("p", "recommendation-detail");
    const heading = createElement("strong", "", `${label}: `);
    const content = createElement(
        "span",
        "",
        formatValue(value)
    );

    row.append(heading, content);
    card.appendChild(row);
}

/* DATA FORMATTING */

function formatValue(value) {
    if (value === null || value === undefined || value === "") {
        return "Not available";
    }

    if (Array.isArray(value)) {
        return value.length > 0
            ? value.map(formatValue).join(", ")
            : "None";
    }

    if (typeof value === "object") {
        return Object.entries(value)
            .map(([key, item]) => `${key}: ${formatValue(item)}`)
            .join(" | ");
    }

    return String(value);
}

function formatDate(timestamp) {
    if (!timestamp) return "Not available";

    const date = new Date(timestamp);

    return Number.isNaN(date.getTime())
        ? "Not available"
        : date.toLocaleString();
}

function sortRecommendations(recommendations) {
    return [...recommendations].sort((a, b) => {
        const dateA = Date.parse(a.created_at_utc);
        const dateB = Date.parse(b.created_at_utc);

        const validA = Number.isFinite(dateA);
        const validB = Number.isFinite(dateB);

        if (!validA && !validB) return 0;
        if (!validA) return 1;
        if (!validB) return -1;

        return dateB - dateA;
    });
}

async function loadFileActivityLookup() {
    try {
        const records = await getLatestFileActivity();
        currentFileActivity = normalizeFileActivity(records);
    } catch (error) {
        currentFileActivity = [];
        console.warn("Could not load file paths for recommendations:", error);
    }
}

function getRecommendationFile(recommendation) {
    if (recommendation.file_id === null || recommendation.file_id === undefined || recommendation.file_id === "") {
        return null;
    }

    const fileId = String(recommendation.file_id);
    const candidates = currentFileActivity.filter(file => file.fileId === fileId && file.path);
    const sourceMatch = recommendation.source_device_id == null
        ? null
        : candidates.find(file => file.deviceId === String(recommendation.source_device_id));
    return sourceMatch ?? (candidates.length === 1 ? candidates[0] : null);
}

async function loadMoveContext() {
    const [capabilityResult, deviceResult] = await Promise.allSettled([
        getCapabilities(),
        getDevices()
    ]);
    const capabilities = capabilityResult.status === "fulfilled"
        ? capabilityResult.value
        : null;
    fileMoveCapability = typeof capabilities?.file_move === "boolean"
        ? capabilities.file_move
        : null;
    currentDevices = deviceResult.status === "fulfilled" && Array.isArray(deviceResult.value)
        ? deviceResult.value
        : [];
}

function recommendationFileName(recommendation) {
    if (recommendation.demoPreview) return recommendation.demoFileName;
    const file = getRecommendationFile(recommendation);
    return file?.name || file?.path || `file ${recommendation.file_id ?? ""}`.trim();
}

function destinationDriveName(recommendation) {
    if (recommendation.demoPreview) return recommendation.demoDestinationLabel;
    const target = currentDevices.find(device =>
        String(device.device_id) === String(recommendation.target_device_id)
    );
    if (!target) return `drive ${recommendation.target_device_id ?? "unavailable"}`;
    const label = target.display_name || target.model || target.name;
    return label && label !== target.device_id
        ? `${label} (${target.device_id})`
        : String(target.device_id);
}

function showMovementToast(recommendation, type, detail = "") {
    if (!movementToastStack) return;
    const key = String(recommendation.recommendation_id);
    const existing = movementToasts.get(key);
    if (existing) {
        window.clearTimeout(existing.dismissTimer);
        window.clearTimeout(existing.removeTimer);
        existing.element.remove();
    }

    const fileName = recommendationFileName(recommendation);
    const destination = destinationDriveName(recommendation);
    const message = type === "started"
        ? `Moving ${fileName} to ${destination}.`
        : type === "completed"
            ? `Successfully moved ${fileName} to ${destination}.`
            : type === "failed"
                ? `Failed to move ${fileName}.${detail ? ` ${detail}` : ""}`
                : type === "preview"
                    ? `Demo preview for ${fileName}. No file was moved.`
                    : `Could not confirm the move for ${fileName}.${detail ? ` ${detail}` : ""}`;
    const toast = createElement("div", "mode-toast movement-toast");
    toast.dataset.kind = type;
    toast.setAttribute("role", type === "failed" ? "alert" : "status");
    toast.setAttribute("aria-atomic", "true");
    toast.classList.add("is-entering");
    const icon = createElement("span", "mode-toast-icon movement-toast-icon", type === "started" ? "↻" : type === "completed" || type === "preview" ? "✓" : "!");
    icon.setAttribute("aria-hidden", "true");
    if (type === "started") icon.classList.add("is-spinning");
    toast.append(icon, createElement("span", "", message));
    movementToastStack.appendChild(toast);

    const entry = { element: toast, dismissTimer: null, removeTimer: null };
    movementToasts.set(key, entry);
    const duration = type === "failed" ? 7000 : type === "started" ? 4500 : 5000;
    entry.dismissTimer = window.setTimeout(() => {
        toast.classList.remove("is-entering");
        toast.classList.add("is-leaving");
        entry.removeTimer = window.setTimeout(() => {
            toast.remove();
            if (movementToasts.get(key) === entry) movementToasts.delete(key);
        }, 240);
    }, duration);
}

function renderMoveAction(card, recommendation) {
    if (recommendation.mode !== "raid0" || recommendation.action !== "move") return;

    const action = createElement("div", "recommendation-move-action");
    if (recommendation.demoPreview) {
        const button = createElement("button", "recommendation-move-button", demoMovePreviewed ? "Previewed" : "Move File");
        button.type = "button";
        button.disabled = demoMovePreviewed;
        button.title = "Preview the move confirmation only; no file operation will be sent.";
        if (!demoMovePreviewed) button.dataset.demoMove = "true";
        const status = createElement("p", "recommendation-move-status", demoMovePreviewed
            ? "Preview completed. No request was sent and no file was moved."
            : "Demo preview only. This button cannot move a real file.");
        action.append(button, status);
        card.appendChild(action);
        return;
    }

    const movement = resolveRecommendationMove(
        recommendation,
        currentFileActivity,
        currentDevices,
        fileMoveCapability
    );
    const state = moveController?.getState(recommendation.recommendation_id);
    const status = createElement("p", "recommendation-move-status");
    let buttonLabel = movement.available ? "Move File" : "Movement unavailable";
    let buttonDisabled = !movement.available;
    let statusText = movement.reason || "Confirm the move before WSD sends it to the backend.";

    if (state?.status === "starting") {
        buttonLabel = "Starting move…";
        buttonDisabled = true;
        statusText = "Sending the confirmed recommendation to CORE.";
    } else if (state?.status === "running") {
        buttonLabel = "Moving…";
        buttonDisabled = true;
        const progress = state.progress !== null && state.progress >= 0 && state.progress <= 1
            ? ` Backend progress: ${Math.round(state.progress * 100)}%.`
            : "";
        const checkError = state.statusError ? ` Status check failed; retrying: ${state.statusError}` : "";
        statusText = `Move action ${state.actionId} is in progress.${progress}${checkError}`;
    } else if (state?.status === "completed") {
        buttonLabel = "Move completed";
        buttonDisabled = true;
        statusText = `Backend confirmed the move to ${state.result}.`;
    } else if (state?.status === "failed") {
        buttonLabel = movement.available && state.retryAllowed ? "Retry Move" : "Movement unavailable";
        buttonDisabled = !movement.available;
        statusText = `Move failed: ${state.error || "The backend did not confirm completion."} Check the file location before retrying.`;
        if (!state.retryAllowed) buttonDisabled = true;
    } else if (state?.status === "unknown") {
        buttonLabel = "Move status unknown";
        buttonDisabled = true;
        statusText = `${state.error} Do not retry until the file location is checked.`;
    }

    const button = createElement("button", "recommendation-move-button", buttonLabel);
    button.type = "button";
    button.disabled = buttonDisabled;
    button.title = buttonDisabled ? statusText : "Review the source and destination, then confirm the move.";
    if (movement.available && state?.status !== "starting" && state?.status !== "running" && state?.status !== "completed") {
        button.dataset.moveRecommendation = recommendation.recommendation_id;
    }
    status.textContent = statusText;
    if (state?.status) status.dataset.state = state.status;
    action.append(button, status);
    card.appendChild(action);
}

function openMoveConfirmation(recommendation, isDemo = false) {
    if (isDemo) {
        pendingMoveRecommendation = recommendation;
        pendingMoveIsDemo = true;
        moveDialogTitle.textContent = "Preview file move";
        moveDialogIntro.textContent = "This is a sample recommendation. Confirming will only preview the interaction; it will not send a request or move a file.";
        moveDialogWarning.textContent = "The source path and destination shown here are examples, not real storage locations.";
        moveDialogName.textContent = recommendation.demoFileName;
        moveDialogPath.textContent = recommendation.demoFilePath;
        moveDialogDestination.textContent = recommendation.demoDestinationLabel;
        moveDialog.showModal();
        return;
    }

    const movement = resolveRecommendationMove(
        recommendation,
        currentFileActivity,
        currentDevices,
        fileMoveCapability
    );
    if (!movement.available || !moveDialog) return;

    pendingMoveRecommendation = recommendation;
    pendingMoveIsDemo = false;
    moveDialogTitle.textContent = "Confirm file move";
    moveDialogIntro.textContent = "This will move the file to another branch in the existing MergerFS pool.";
    moveDialogWarning.textContent = "Make sure the file is not open for writing. The destination branch must contain the matching parent directory.";
    moveDialogName.textContent = movement.file.name || movement.file.path;
    moveDialogPath.textContent = movement.file.path;
    moveDialogDestination.textContent = destinationDriveName(recommendation);
    moveDialog.showModal();
}

function initializeMoveActions() {
    moveController = createRecommendationMoveController({
        execute: executeRecommendedFileMove,
        getStatus: getFileActionStatus,
        onChange: (_recommendationId, state) => {
            renderRecommendations(currentRecommendations);
            if (state.status === "completed") {
                void loadFileActivityLookup().then(() => renderRecommendations(currentRecommendations));
            }
        },
        onToast: ({ type, recommendation, message }) => showMovementToast(recommendation, type, message)
    });

    container.addEventListener("click", event => {
        const demoButton = event.target.closest?.("[data-demo-move]");
        if (demoButton) {
            openMoveConfirmation(demoMoveRecommendation, true);
            return;
        }
        const button = event.target.closest?.("[data-move-recommendation]");
        if (!button) return;
        const recommendation = currentRecommendations.find(item =>
            item.recommendation_id === button.dataset.moveRecommendation
        );
        if (recommendation) openMoveConfirmation(recommendation);
    });
    cancelMoveButton?.addEventListener("click", () => moveDialog.close());
    moveDialog?.addEventListener("close", () => {
        pendingMoveRecommendation = null;
        pendingMoveIsDemo = false;
    });
    confirmMoveButton?.addEventListener("click", () => {
        const recommendation = pendingMoveRecommendation;
        if (!recommendation || !moveController) return;
        const isDemo = pendingMoveIsDemo;
        pendingMoveRecommendation = null;
        pendingMoveIsDemo = false;
        moveDialog.close();
        if (isDemo) {
            demoMovePreviewed = true;
            renderRecommendations(currentRecommendations);
            showMovementToast(recommendation, "preview");
            return;
        }
        void moveController.start(recommendation);
    });

    moveDemoButton?.addEventListener("click", () => {
        showMoveDemo = !showMoveDemo;
        demoMovePreviewed = false;
        moveDemoButton.textContent = showMoveDemo ? "Hide Move Preview" : "Show Move Preview";
        moveDemoButton.setAttribute("aria-pressed", String(showMoveDemo));
        renderRecommendations(currentRecommendations);
    });

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) moveController.pause();
        else moveController.resume();
    });
    window.addEventListener("pagehide", () => moveController.pause());
    window.addEventListener("pageshow", () => moveController.resume());
    window.addEventListener("beforeunload", () => {
        moveController.dispose();
        for (const entry of movementToasts.values()) {
            window.clearTimeout(entry.dismissTimer);
            window.clearTimeout(entry.removeTimer);
        }
        movementToasts.clear();
    });
}

/* EMPTY AND ERROR STATES */

function showMessage(
    message,
    className = "recommendations-empty"
) {
    container.replaceChildren(
        createElement("p", className, message)
    );
}

/* RECOMMENDATION RENDERING */

function renderRecommendations(recommendations) {
    if (!Array.isArray(recommendations)) {
        throw new Error("Expected a list of recommendations.");
    }

    const validRecommendations = recommendations.filter(
        recommendation =>
            recommendation !== null &&
            typeof recommendation === "object" &&
            !Array.isArray(recommendation)
    );

    currentRecommendations = validRecommendations;
    const previewModeMatches = modeSelect?.value !== "ssd_caching";
    const displayRecommendations = showMoveDemo && previewModeMatches
        ? [...validRecommendations, demoMoveRecommendation]
        : validRecommendations;
    let sortedRecommendations = sortRecommendations(displayRecommendations);
    if (sortSelect?.value === "benefit") {
        sortedRecommendations.sort((a, b) => {
            const av = typeof a.estimated_benefit === "number" ? a.estimated_benefit : null;
            const bv = typeof b.estimated_benefit === "number" ? b.estimated_benefit : null;
            if (av === null && bv === null) return 0;
            if (av === null) return 1;
            if (bv === null) return -1;
            return bv - av;
        });
    }
    const query = (filterInput?.value ?? "").trim().toLowerCase();
    if (query) {
        sortedRecommendations = sortedRecommendations.filter(item =>
            JSON.stringify(item).toLowerCase().includes(query)
        );
    }

    container.replaceChildren();

    if (sortedRecommendations.length === 0) {
        showMessage(
            "No recommendations are currently available."
        );

        return 0;
    }

    for (const recommendation of sortedRecommendations) {
        const card = createElement(
            "article",
            "recommendation-card"
        );
        if (recommendation.demoPreview) card.dataset.demoPreviewCard = "true";

        /* HEADER */

        const header = createElement(
            "div",
            "recommendation-card-header"
        );

        const titleGroup = createElement(
            "div",
            "recommendation-title-group"
        );

        const hasFile = recommendation.file_id !== null &&
            recommendation.file_id !== undefined &&
            recommendation.file_id !== "";

        const file = recommendation.demoPreview
            ? { name: recommendation.demoFileName, path: recommendation.demoFilePath }
            : getRecommendationFile(recommendation);
        const title = file?.name || file?.path || (hasFile
            ? `File ID: ${recommendation.file_id}`
            : "Storage recommendation");

        const mode = recommendation.mode ?? "Unknown mode";
        const action = recommendation.action ?? "Unknown action";

        titleGroup.append(
            createElement("h3", "", title),
            createElement(
                "p",
                "recommendation-subtitle",
                `${mode} · ${action}`
            )
        );

        const approvalRequired =
            recommendation.requires_approval === true;

        const approvalBadge = createElement(
            "span",
            recommendation.demoPreview
                ? "recommendation-badge demo-preview-badge"
                : approvalRequired
                ? "recommendation-badge approval-required"
                : "recommendation-badge",
            recommendation.demoPreview
                ? "Demo preview"
                : approvalRequired
                ? "Approval required"
                : "No approval flagged"
        );

        header.append(titleGroup, approvalBadge);
        card.appendChild(header);

        /* DETAILS */

        addDetail(card, "Reason", recommendation.reason);
        if (file?.path) addDetail(card, "File path", file.path);
        addDetail(card, "Source device", recommendation.source_device_id);
        addDetail(card, "Target device", recommendation.target_device_id);
        addDetail(card, "Estimated benefit", recommendation.estimated_benefit);
        addDetail(card, "Generated", formatDate(recommendation.created_at_utc));

        /* CONSTRAINTS */

        const constraints = Array.isArray(recommendation.constraints)
            ? recommendation.constraints
            : [];

        card.appendChild(
            createElement("h4", "", "Constraints")
        );

        if (constraints.length === 0) {
            card.appendChild(
                createElement("p", "", "No constraints provided.")
            );
        } else {
            const list = createElement(
                "ul",
                "recommendation-constraints"
            );

            for (const constraint of constraints) {
                list.appendChild(
                    createElement("li", "", formatValue(constraint))
                );
            }

            card.appendChild(list);
        }

        /* IDENTIFIER */

        card.appendChild(
            createElement(
                "p",
                "recommendation-id",
                recommendation.demoPreview
                    ? "Demo preview card; not sent to the backend"
                    : `ID: ${recommendation.recommendation_id ?? "Unavailable"}`
            )
        );

        renderMoveAction(card, recommendation);

        container.appendChild(card);
    }

    return sortedRecommendations.length;
}

/* LOAD SAVED RECOMMENDATIONS */

async function loadRecommendations() {
    statusElement.textContent =
        "Loading saved recommendations...";

    try {
        const mode = modeSelect?.value || undefined;
        const [recommendations] = await Promise.all([
            getRecommendations(mode),
            loadFileActivityLookup(),
            loadMoveContext()
        ]);

        const displayedCount =
            renderRecommendations(recommendations);
        const previewShown = Boolean(container.querySelector("[data-demo-preview-card]"));
        const savedCount = displayedCount - (previewShown ? 1 : 0);

        const modeLabel = mode === "raid0"
            ? "RAID 0 / file-level pooling"
            : mode === "ssd_caching" ? "SSD caching" : "all modes";
        statusElement.textContent =
            `${savedCount} saved recommendation(s) for ${modeLabel}.${previewShown ? " A demo move preview card is also shown." : ""}`;

    } catch (error) {
        console.error("Failed to load recommendations:", error);

        statusElement.textContent =
            `Could not load recommendations: ${error.message}`;

        showMessage(
            "Unable to load recommendations. Please try again.",
            "recommendations-error"
        );
    }
}

/* REFRESH RECOMMENDATIONS */

async function handleRefresh() {
    if (isRefreshing) return;

    isRefreshing = true;
    updateRefreshAvailability();
    refreshButton.textContent = "Refreshing...";
    statusElement.textContent = "Generating recommendations...";

    try {
        // The backend generates and saves recommendations before returning.
        // “All modes” filters saved results; the backend defaults refresh to
        // RAID 0, so make the generated mode explicit in that case.
        const mode = modeSelect?.value || "raid0";
        const generated = await refreshRecommendations(mode);

        if (!Array.isArray(generated)) {
            throw new Error(
                "Expected the refresh response data to be an array."
            );
        }

        await Promise.all([loadFileActivityLookup(), loadMoveContext()]);

        const generatedCount =
            renderRecommendations(generated);
        const previewShown = Boolean(container.querySelector("[data-demo-preview-card]"));
        const generatedRealCount = generatedCount - (previewShown ? 1 : 0);

        const modeLabel = mode === "ssd_caching"
            ? "SSD Caching"
            : "RAID 0 / file-level pooling";
        statusElement.textContent =
            `${generatedRealCount} ${modeLabel} recommendation(s) generated and saved.${previewShown ? " A demo move preview card is also shown." : ""}`;

    } catch (error) {
        console.error("Failed to refresh recommendations:", error);

        statusElement.textContent =
            `Could not generate recommendations: ${error.message}`;

        // Do not erase previously displayed recommendations on failure.
        if (container.childElementCount === 0) {
            showMessage(
                "Recommendation generation failed. Please try again.",
                "recommendations-error"
            );
        }

    } finally {
        isRefreshing = false;
        updateRefreshAvailability();
        refreshButton.textContent = "Refresh Recommendations";
    }
}

/* INITIALIZATION */

if (!container || !statusElement || !refreshButton) {
    console.error(
        "Recommendations page is missing one or more required HTML elements."
    );
} else {
    initializeMoveActions();
    refreshButton.addEventListener("click", handleRefresh);
    modeSelect?.addEventListener("change", () => {
        updateRefreshAvailability();
        loadRecommendations();
    });
    filterInput?.addEventListener("input", () => renderRecommendations(currentRecommendations));
    sortSelect?.addEventListener("change", () => renderRecommendations(currentRecommendations));
    updateRefreshAvailability();
    loadRecommendations();
}
