// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import {
    createFileSubscription,
    deleteFileSubscription,
    executeFileMove,
    getCapabilities,
    getFileActionStatus,
    getFileSubscriptions,
    getLatestFileActivity,
    isMockDataEnabled,
    setMockDataEnabled
} from "./api.js";
import { filterAndSortFileActivity, normalizeFileActivity, summarizeFileActivity } from "./fileIoApi.js";
import { createRollingFileActivityHistory, rankFileActivity } from "./fileIoHistory.js";
import { renderFileActivityHistory } from "./fileIoHistoryCharts.js";

let pageRows = null;
let selectedFile = null;
let reportedCapability = null;
let isLoading = false;
let lastLoadError = null;
let refreshTimer = null;
let pageIsActive = true;
let modeGeneration = 0;
let refreshPending = false;
let fileMoveCapability = null;
let subscriptionsMutationPending = false;
let activeMoveActionId = null;
let movePollTimer = null;
let moveRequestPending = false;
const liveFileHistory = createRollingFileActivityHistory();
const mockFileHistory = createRollingFileActivityHistory();

const MAX_RENDERED_ROWS = 500;
const POLL_INTERVAL_MS = 5000;
const valid = value => typeof value === "number" && Number.isFinite(value) && value >= 0;
const unavailable = "Unavailable";
const isAbsolutePath = path => path.startsWith("/") || /^[A-Za-z]:[\\/]/.test(path) || path.startsWith("\\\\");

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function formatBytes(value) {
    if (!valid(value)) return unavailable;
    const units = ["bytes", "KB", "MB", "GB", "TB", "PB"];
    let amount = value;
    let unit = 0;
    while (amount >= 1024 && unit < units.length - 1) {
        amount /= 1024;
        unit += 1;
    }
    return `${amount.toLocaleString("en-CA", { maximumFractionDigits: unit ? 2 : 0 })} ${units[unit]}`;
}

function formatCount(value) {
    return valid(value) ? value.toLocaleString("en-CA", { maximumFractionDigits: 0 }) : unavailable;
}

function formatRate(value) {
    return valid(value) ? `${formatBytes(value)}/s` : unavailable;
}

function formatTime(value) {
    const time = Date.parse(value);
    return Number.isFinite(time) ? new Date(time).toLocaleString() : unavailable;
}

function totalBytes(row) {
    return valid(row.readBytes) && valid(row.writeBytes)
        ? row.readBytes + row.writeBytes
        : null;
}

function totalOperations(row) {
    return valid(row.readOps) && valid(row.writeOps)
        ? row.readOps + row.writeOps
        : null;
}

function formatAvailableTotal(rows, field, formatter) {
    if (rows.length === 0) return "No activity";
    const values = rows.map(row => row[field]).filter(valid);
    if (!values.length) return "No measurements";
    const subtotal = values.reduce((total, value) => total + value, 0);
    return `${values.length < rows.length ? "At least " : ""}${formatter(subtotal)}`;
}

function renderSummary(rows, observations = []) {
    if (rows === null) {
        setText("file-total-count", "Waiting for activity");
        setText("file-total-read-bytes", "Waiting for activity");
        setText("file-total-write-bytes", "Waiting for activity");
        setText("file-total-read-ops", "Waiting for activity");
        setText("file-total-write-ops", "Waiting for activity");
        setText("file-most-active", "Collecting activity");
        document.getElementById("file-most-active").removeAttribute("title");
        return;
    }

    setText("file-total-count", rows.length.toLocaleString("en-CA"));
    setText("file-total-read-bytes", formatAvailableTotal(rows, "readBytes", formatBytes));
    setText("file-total-write-bytes", formatAvailableTotal(rows, "writeBytes", formatBytes));
    setText("file-total-read-ops", formatAvailableTotal(rows, "readOps", formatCount));
    setText("file-total-write-ops", formatAvailableTotal(rows, "writeOps", formatCount));

    const highestRate = rankFileActivity(observations, 1)[0];
    const currentWindowMostActive = summarizeFileActivity(rows).mostActiveFile;
    const mostActive = highestRate ?? currentWindowMostActive;
    const mostActiveElement = document.getElementById("file-most-active");
    if (mostActive?.path || mostActive?.name) {
        mostActiveElement.textContent = mostActive.name || mostActive.path;
        mostActiveElement.title = highestRate
            ? `Highest average observed throughput across available recent activity samples: ${mostActive.path || mostActive.name}`
            : `Highest total I/O among files with complete byte measurements in the latest response: ${mostActive.path || mostActive.name}`;
    } else {
        mostActiveElement.textContent = rows.length ? "Insufficient measurements" : "No activity";
        mostActiveElement.title = "A file cannot be ranked until its activity can be measured.";
    }
}

function renderDetails(row) {
    const grid = document.getElementById("file-detail-grid");
    grid.replaceChildren();
    if (!row) {
        setText("file-detail-status", "Select a file with returned activity to inspect its details.");
        updateMoveControl();
        return;
    }

    setText("file-detail-status", row.path || row.name || "Selected file");
    const details = [
        ["Full path", row.path], ["File name", row.name], ["Host ID", row.hostId],
        ["File ID", row.fileId], ["Device ID", row.deviceId], ["Collection source", row.source],
        ["Read bytes", formatBytes(row.readBytes)], ["Write bytes", formatBytes(row.writeBytes)],
        ["Read operations", formatCount(row.readOps)], ["Write operations", formatCount(row.writeOps)],
        ["Total bytes transferred", formatBytes(totalBytes(row))],
        ["File size", formatBytes(row.fileSizeBytes)],
        ["Read throughput", formatRate(row.readBytesPerSec)], ["Write throughput", formatRate(row.writeBytesPerSec)],
        ["Window start", formatTime(row.windowStartUtc)], ["Window end", formatTime(row.windowEndUtc)],
        ["Observed timestamp", formatTime(row.observedAt)]
    ];

    for (const [label, value] of details) {
        const item = document.createElement("div");
        item.className = "file-detail-item";
        const heading = document.createElement("span");
        heading.textContent = label;
        const content = document.createElement("strong");
        content.textContent = value == null ? unavailable : String(value);
        item.append(heading, content);
        grid.appendChild(item);
    }
    updateMoveControl();
}

function updateMoveControl() {
    const button = document.getElementById("file-move-button");
    const destination = document.getElementById("file-move-destination");
    if (!button || !destination) return;

    const previewMode = isMockDataEnabled();
    button.disabled = fileMoveCapability === null || !selectedFile?.path || previewMode || activeMoveActionId !== null || moveRequestPending;
    destination.disabled = fileMoveCapability === null || previewMode || activeMoveActionId !== null || moveRequestPending;
}

function filteredRows() {
    return filterAndSortFileActivity(pageRows ?? [], {
        query: document.getElementById("file-search").value,
        activity: document.getElementById("file-activity-filter").value,
        sort: document.getElementById("file-sort").value
    });
}

function makeCell(row, value, { title = null, className = "" } = {}) {
    const cell = document.createElement("td");
    cell.textContent = value;
    if (title) cell.title = title;
    if (className) cell.className = className;
    row.appendChild(cell);
}

function renderTable() {
    const body = document.getElementById("file-activity-body");
    const rows = filteredRows();
    body.replaceChildren();

    for (const row of rows.slice(0, MAX_RENDERED_ROWS)) {
        const tr = document.createElement("tr");
        tr.tabIndex = 0;
        tr.setAttribute("role", "button");
        makeCell(tr, row.path || unavailable, { title: row.path, className: "file-path-cell" });
        makeCell(tr, row.name || unavailable, { title: row.name, className: "file-name-cell" });
        makeCell(tr, formatBytes(row.readBytes));
        makeCell(tr, formatBytes(row.writeBytes));
        makeCell(tr, formatBytes(totalBytes(row)));
        makeCell(tr, formatCount(row.readOps));
        makeCell(tr, formatCount(row.writeOps));
        makeCell(tr, formatCount(totalOperations(row)));
        makeCell(tr, formatBytes(row.fileSizeBytes));
        makeCell(tr, row.source || unavailable, { title: row.source, className: "file-source-cell" });

        const key = row.fileId || row.path;
        if (selectedFile && key === (selectedFile.fileId || selectedFile.path)) tr.classList.add("selected-file-row");
        const select = () => {
            selectedFile = row;
            renderTable();
            renderDetails(row);
            if (activeMoveActionId !== null || moveRequestPending) {
                return;
            }
            if (isMockDataEnabled()) {
                setText("file-move-status", "Move actions are disabled while viewing mock preview data.");
            } else if (fileMoveCapability === true) {
                setText("file-move-status", "Selected live file. Enter a destination branch mount before starting a move.");
            } else if (fileMoveCapability === false) {
                setText("file-move-status", "The backend reports file movement unavailable. You can try the implemented route after confirming the move; its result may be incomplete.");
            } else {
                setText("file-move-status", "Move availability is unknown; move requests remain disabled until the backend reports support.");
            }
        };
        tr.addEventListener("click", select);
        tr.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                select();
            }
        });
        body.appendChild(tr);
    }

    if (!rows.length) {
        const tr = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 10;
        cell.textContent = pageRows === null
            ? lastLoadError ? "File activity could not be loaded. Use refresh to retry." : "Loading file activity..."
            : pageRows.length ? "No files match the current search and activity filter." : "No file activity records were returned for this measurement window.";
        tr.appendChild(cell);
        body.appendChild(tr);
    }

    let tableStatus;
    if (pageRows === null) {
        tableStatus = lastLoadError ? "File activity is unavailable." : "Loading the latest file activity...";
    } else if (!pageRows.length) {
        tableStatus = "No file activity records were returned for this measurement window.";
    } else {
        tableStatus = rows.length > MAX_RENDERED_ROWS
            ? `Showing the first ${MAX_RENDERED_ROWS} of ${rows.length} matching records (${pageRows.length} total).`
            : `${rows.length} of ${pageRows.length} file record(s) shown.`;
    }
    setText("file-table-status", tableStatus);
}

function describeEmptyResponse() {
    if (reportedCapability === false) {
        return "The API returned no file activity records, and the backend reports file-access metrics unavailable on this platform.";
    }
    if (reportedCapability === true) {
        return "The API returned no file activity records. The backend reports file-access capability, but this response does not establish that measured activity was zero.";
    }
    return "The API returned no file activity records for the latest measurement window.";
}

function renderSubscriptions(records) {
    if (!Array.isArray(records)) {
        throw new Error("Expected file subscription API data to be an array.");
    }

    const body = document.getElementById("file-subscriptions-body");
    body.replaceChildren();

    if (records.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 4;
        cell.textContent = "The backend returned no active file or folder subscriptions.";
        row.appendChild(cell);
        body.appendChild(row);
        return;
    }

    for (const record of records) {
        if (!record || typeof record !== "object" || Array.isArray(record)) {
            throw new Error("The subscription response contains an invalid record.");
        }

        const row = document.createElement("tr");
        const path = typeof record.path === "string" ? record.path : null;
        for (const value of [path ?? "Path unavailable", record.target_type ?? "Unavailable", record.status ?? "Unavailable"]) {
            const cell = document.createElement("td");
            cell.textContent = String(value);
            row.appendChild(cell);
        }

        const actionCell = document.createElement("td");
        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.textContent = "Stop tracking";
        removeButton.dataset.hasPath = String(Boolean(path));
        removeButton.disabled = !path || isMockDataEnabled() || subscriptionsMutationPending;
        removeButton.addEventListener("click", () => {
            if (path) void removeSubscription(path);
        });
        actionCell.appendChild(removeButton);
        row.appendChild(actionCell);
        body.appendChild(row);
    }
}

function updateSubscriptionControls() {
    const disabled = isMockDataEnabled() || subscriptionsMutationPending;
    const pathInput = document.getElementById("file-subscription-path");
    const addButton = document.getElementById("file-subscription-add");
    if (pathInput) pathInput.disabled = disabled;
    if (addButton) addButton.disabled = disabled;
    document.querySelectorAll("#file-subscriptions-body button").forEach(button => {
        button.disabled = disabled || button.dataset.hasPath !== "true";
    });
}

async function refreshSubscriptions() {
    const status = document.getElementById("file-subscriptions-status");
    status.textContent = "Loading subscriptions from the backend...";
    try {
        const records = await getFileSubscriptions();
        renderSubscriptions(records);
        status.textContent = `${records.length} active subscription(s) returned by the backend.`;
        updateSubscriptionControls();
        return true;
    } catch (error) {
        const body = document.getElementById("file-subscriptions-body");
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 4;
        cell.textContent = "Subscriptions could not be loaded.";
        row.appendChild(cell);
        body.replaceChildren(row);
        status.textContent = `Could not load file subscriptions: ${error.message}`;
        return false;
    }
}

async function addSubscription() {
    if (isMockDataEnabled() || subscriptionsMutationPending) return;
    const input = document.getElementById("file-subscription-path");
    const path = input.value.trim();
    const status = document.getElementById("file-subscriptions-status");
    if (!path) {
        status.textContent = "Enter a file or folder path first.";
        input.focus();
        return;
    }
    if (!isAbsolutePath(path)) {
        status.textContent = "Enter an absolute file or folder path.";
        input.focus();
        return;
    }

    subscriptionsMutationPending = true;
    updateSubscriptionControls();
    status.textContent = "Sending the tracking request to the backend...";
    try {
        const trackedPath = await createFileSubscription(path);
        if (typeof trackedPath !== "string") {
            throw new Error("The backend did not return the subscribed path.");
        }
        input.value = "";
        await refreshSubscriptions();
    } catch (error) {
        await refreshSubscriptions();
        status.textContent = `Tracking request failed: ${error.message}. Backend tracking state may have changed; refresh the list before retrying.`;
    } finally {
        subscriptionsMutationPending = false;
        updateSubscriptionControls();
    }
}

async function removeSubscription(path) {
    if (isMockDataEnabled() || subscriptionsMutationPending) return;
    const status = document.getElementById("file-subscriptions-status");
    subscriptionsMutationPending = true;
    updateSubscriptionControls();
    status.textContent = "Sending the stop-tracking request to the backend...";
    try {
        const removedPath = await deleteFileSubscription(path);
        if (typeof removedPath !== "string") {
            throw new Error("The backend did not return the unsubscribed path.");
        }
        await refreshSubscriptions();
    } catch (error) {
        await refreshSubscriptions();
        status.textContent = `Stop-tracking request failed: ${error.message}. Refresh the list to check the current backend state.`;
    } finally {
        subscriptionsMutationPending = false;
        updateSubscriptionControls();
    }
}

async function pollMoveStatus(actionId) {
    if (!pageIsActive || activeMoveActionId !== actionId) return;
    try {
        const action = await getFileActionStatus(actionId);
        if (!action || typeof action !== "object" || typeof action.is_running !== "boolean") {
            throw new Error("The action status response is missing is_running.");
        }

        const progress = typeof action.progress === "number" && Number.isFinite(action.progress)
            ? ` Backend progress value: ${action.progress}.`
            : " Backend progress is unavailable.";
        if (action.is_running) {
            setText("file-move-status", `Move ${actionId} is running.${progress}`);
            if (pageIsActive) movePollTimer = window.setTimeout(() => pollMoveStatus(actionId), 1000);
            return;
        }

        activeMoveActionId = null;
        const result = typeof action.result === "string" ? action.result : null;
        if (!result) {
            setText("file-move-status", `Move ${actionId} stopped without a result.${progress}`);
        } else if (/^[A-Z][A-Z0-9_]+$/.test(result)) {
            setText("file-move-status", `Move ${actionId} ended with backend error ${result}.${progress}`);
        } else {
            setText("file-move-status", `Move ${actionId} completed. Backend result: ${result}.${progress}`);
            void refreshFileActivity();
        }
        updateMoveControl();
    } catch (error) {
        setText("file-move-status", `Could not check move ${actionId}: ${error.message}. Retrying shortly.`);
        if (pageIsActive) movePollTimer = window.setTimeout(() => pollMoveStatus(actionId), 4000);
    }
}

async function startFileMove() {
    if (fileMoveCapability === null || !selectedFile?.path || isMockDataEnabled() || activeMoveActionId !== null || moveRequestPending) return;

    const destination = document.getElementById("file-move-destination").value.trim();
    if (!destination) {
        setText("file-move-status", "Enter a destination branch mount path first.");
        document.getElementById("file-move-destination").focus();
        return;
    }
    if (!isAbsolutePath(selectedFile.path) || !isAbsolutePath(destination)) {
        setText("file-move-status", "The selected file and destination branch must use absolute paths.");
        return;
    }

    const capabilityWarning = fileMoveCapability === false
        ? " The backend reports file movement unavailable; the request may fail or start without returning a trackable action ID. Verify the file location before any retry."
        : "";
    const confirmed = window.confirm(
        `Move ${selectedFile.path} to ${destination}? This starts a live file move in the MergerFS pool. The destination branch must already contain the matching parent directory.${capabilityWarning}`
    );
    if (!confirmed) return;

    moveRequestPending = true;
    setText("file-move-status", "Sending the move request to the backend...");
    updateMoveControl();
    try {
        const actionId = await executeFileMove(selectedFile.path, destination);
        if (typeof actionId !== "string" || !actionId) {
            throw new Error("The backend did not return a move action ID.");
        }
        activeMoveActionId = actionId;
        setText("file-move-status", `Move started with action ID ${actionId}. Checking progress...`);
        updateMoveControl();
        void pollMoveStatus(actionId);
    } catch (error) {
        setText("file-move-status", `Move request failed: ${error.message}. No action ID was returned, so verify the file location before retrying.`);
    } finally {
        moveRequestPending = false;
        updateMoveControl();
    }
}

function renderSourceStatus() {
    const mock = isMockDataEnabled();
    const sourceSelector = document.getElementById("file-data-source");
    const sourceStatus = document.getElementById("file-source-status");
    const dataTag = document.getElementById("file-data-tag");
    if (sourceSelector) sourceSelector.value = mock ? "mock" : "live";
    if (sourceStatus) {
        sourceStatus.textContent = mock
            ? "MOCK PREVIEW - sample data, not live system activity"
            : "LIVE API - showing backend responses only";
        sourceStatus.dataset.mode = mock ? "mock" : "live";
    }
    if (dataTag) dataTag.textContent = mock ? "Mock preview data" : "Live API data";
    updateSubscriptionControls();
    updateMoveControl();
    renderFileActivityHistory(currentFileHistory().getObservations(), isMockDataEnabled() ? "mock" : "live");
}

function currentFileHistory() {
    return isMockDataEnabled() ? mockFileHistory : liveFileHistory;
}

async function refreshFileActivity() {
    if (isLoading) {
        refreshPending = true;
        return;
    }
    isLoading = true;
    window.clearTimeout(refreshTimer);
    refreshPending = false;
    const requestGeneration = modeGeneration;
    const requestIsMock = isMockDataEnabled();
    const refreshButton = document.getElementById("file-refresh-button");
    refreshButton.disabled = true;
    setText("file-io-status", "Requesting the latest file activity...");
    setText("file-updated-status", "Request in progress...");
    if (pageRows === null) {
        setText("file-table-status", "Loading the latest file activity...");
        renderTable();
    }

    try {
        const records = await getLatestFileActivity();
        if (requestGeneration !== modeGeneration) return;
        pageRows = normalizeFileActivity(records);
        currentFileHistory().record(pageRows);
        const observations = currentFileHistory().getObservations();
        renderFileActivityHistory(observations, requestIsMock ? "mock" : "live");
        lastLoadError = null;
        if (selectedFile) {
            const selectedKey = selectedFile.fileId || selectedFile.path;
            selectedFile = pageRows.find(row => (row.fileId || row.path) === selectedKey) ?? null;
        }
        renderSummary(pageRows, observations);
        renderTable();
        renderDetails(selectedFile);

        const checkedAt = new Date().toLocaleTimeString();
        setText("file-updated-status", `Last checked ${checkedAt}.`);
        setText("file-io-status", requestIsMock
            ? `MOCK PREVIEW: ${pageRows.length.toLocaleString("en-CA")} sample file record(s). These are not live system activity.`
            : pageRows.length
            ? `${pageRows.length.toLocaleString("en-CA")} file activity record(s) returned by the live API.`
            : describeEmptyResponse());
    } catch (error) {
        if (requestGeneration !== modeGeneration) return;
        renderFileActivityHistory(currentFileHistory().getObservations(), requestIsMock ? "mock" : "live");
        lastLoadError = error?.message || "Request failed.";
        if (pageRows === null) {
            renderSummary(null);
            renderTable();
            renderDetails(null);
        }
        setText("file-io-status", `Could not load file activity: ${lastLoadError}`);
        setText("file-updated-status", pageRows === null ? "No successful response yet." : "Refresh failed; showing the last successful response.");
    } finally {
        isLoading = false;
        refreshButton.disabled = false;
        if (pageIsActive && refreshPending) {
            refreshPending = false;
            void refreshFileActivity();
        } else if (pageIsActive) {
            refreshTimer = window.setTimeout(refreshFileActivity, POLL_INTERVAL_MS);
        }
    }
}

async function loadCapabilities() {
    const generation = modeGeneration;
    try {
        const capabilities = await getCapabilities();
        if (generation === modeGeneration && !isMockDataEnabled()) {
            const fileAccessValue = capabilities && Object.hasOwn(capabilities, "file_access_metrics")
                ? capabilities.file_access_metrics
                : null;
            const fileMoveValue = capabilities && Object.hasOwn(capabilities, "file_move")
                ? capabilities.file_move
                : null;
            reportedCapability = typeof fileAccessValue === "boolean" ? fileAccessValue : null;
            fileMoveCapability = typeof fileMoveValue === "boolean" ? fileMoveValue : null;
            setText("file-move-status", fileMoveCapability === true
                ? "The backend reports file movement support. Starting a move changes the live storage system."
                : fileMoveCapability === false
                ? "The backend reports file movement unavailable. The implemented move route can still be tried after confirmation; its result may be incomplete."
                : "The backend did not report file movement support; move requests remain disabled.");
            updateMoveControl();
        }
    } catch (error) {
        if (generation === modeGeneration) {
            reportedCapability = null;
            fileMoveCapability = null;
            setText("file-move-status", `Could not determine move availability: ${error.message}. Move requests remain disabled.`);
            updateMoveControl();
        }
    }
}

async function changeDataSource() {
    const source = document.getElementById("file-data-source").value;
    setMockDataEnabled(source === "mock");
    modeGeneration += 1;
    const selectedGeneration = modeGeneration;
    reportedCapability = null;
    fileMoveCapability = null;
    lastLoadError = null;
    pageRows = null;
    selectedFile = null;
    window.clearTimeout(refreshTimer);
    renderSourceStatus();
    renderSummary(null);
    renderTable();
    renderDetails(null);
    setText("file-io-status", isMockDataEnabled()
        ? "Loading mock preview records; no live activity is being measured."
        : "Loading file activity from the live backend API.");
    setText("file-move-status", isMockDataEnabled()
        ? "Move actions are disabled while viewing mock preview data."
        : "Loading move availability from the backend...");

    if (!isMockDataEnabled()) await loadCapabilities();
    if (selectedGeneration !== modeGeneration) return;
    await refreshFileActivity();
}

async function initialize() {
    const search = document.getElementById("file-search");
    const activityFilter = document.getElementById("file-activity-filter");
    const sort = document.getElementById("file-sort");
    const source = document.getElementById("file-data-source");
    document.getElementById("file-refresh-button").addEventListener("click", refreshFileActivity);
    document.getElementById("file-subscription-add").addEventListener("click", addSubscription);
    document.getElementById("file-subscriptions-refresh").addEventListener("click", refreshSubscriptions);
    document.getElementById("file-subscription-path").addEventListener("keydown", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            addSubscription();
        }
    });
    document.getElementById("file-move-button").addEventListener("click", startFileMove);
    source.addEventListener("change", changeDataSource);
    search.addEventListener("input", renderTable);
    activityFilter.addEventListener("change", renderTable);
    sort.addEventListener("change", renderTable);
    renderSourceStatus();
    renderSummary(null);
    renderTable();
    void refreshSubscriptions();

    const initialGeneration = modeGeneration;
    if (!isMockDataEnabled()) await loadCapabilities();
    if (initialGeneration === modeGeneration) await refreshFileActivity();
}

initialize();

function handleVisibilityChange() {
    pageIsActive = !document.hidden;
    if (!pageIsActive) {
        window.clearTimeout(refreshTimer);
        window.clearTimeout(movePollTimer);
        return;
    }
    if (activeMoveActionId !== null) void pollMoveStatus(activeMoveActionId);
    if (!isLoading) void refreshFileActivity();
}

function handlePageHide() {
    pageIsActive = false;
    window.clearTimeout(refreshTimer);
    window.clearTimeout(movePollTimer);
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    window.removeEventListener("pagehide", handlePageHide);
}

document.addEventListener("visibilitychange", handleVisibilityChange);
window.addEventListener("pagehide", handlePageHide, { once: true });
