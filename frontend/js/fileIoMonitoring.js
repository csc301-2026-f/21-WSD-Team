// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { getCapabilities, getLatestFileActivity, isMockDataEnabled, setMockDataEnabled } from "./api.js";
import { filterAndSortFileActivity, normalizeFileActivity, summarizeFileActivity } from "./fileIoApi.js";

let pageRows = null;
let selectedFile = null;
let reportedCapability = null;
let isLoading = false;
let lastLoadError = null;
let refreshTimer = null;
let pageIsActive = true;
let modeGeneration = 0;
let refreshPending = false;

const MAX_RENDERED_ROWS = 500;
const POLL_INTERVAL_MS = 8000;
const valid = value => typeof value === "number" && Number.isFinite(value) && value >= 0;
const unavailable = "Unavailable";

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

function renderSummary(rows) {
    if (rows === null) {
        for (const id of ["file-total-count", "file-total-read-bytes", "file-total-write-bytes", "file-total-read-ops", "file-total-write-ops", "file-most-active"]) {
            setText(id, unavailable);
        }
        return;
    }

    const summary = summarizeFileActivity(rows);
    setText("file-total-count", summary.fileCount.toLocaleString("en-CA"));
    setText("file-total-read-bytes", formatBytes(summary.totalReadBytes));
    setText("file-total-write-bytes", formatBytes(summary.totalWriteBytes));
    setText("file-total-read-ops", formatCount(summary.totalReadOps));
    setText("file-total-write-ops", formatCount(summary.totalWriteOps));
    setText("file-most-active", summary.mostActiveFile?.path || summary.mostActiveFile?.name || unavailable);
}

function renderDetails(row) {
    const grid = document.getElementById("file-detail-grid");
    grid.replaceChildren();
    if (!row) {
        setText("file-detail-status", "Select a file with returned activity to inspect its details.");
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
        makeCell(tr, row.name || unavailable, { title: row.name });
        makeCell(tr, formatBytes(row.readBytes));
        makeCell(tr, formatBytes(row.writeBytes));
        makeCell(tr, formatBytes(totalBytes(row)));
        makeCell(tr, formatCount(row.readOps));
        makeCell(tr, formatCount(row.writeOps));
        makeCell(tr, formatCount(totalOperations(row)));
        makeCell(tr, formatBytes(row.fileSizeBytes));
        makeCell(tr, row.source || unavailable);

        const key = row.fileId || row.path;
        if (selectedFile && key === (selectedFile.fileId || selectedFile.path)) tr.classList.add("selected-file-row");
        const select = () => {
            selectedFile = row;
            renderTable();
            renderDetails(row);
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
        lastLoadError = null;
        if (selectedFile) {
            const selectedKey = selectedFile.fileId || selectedFile.path;
            selectedFile = pageRows.find(row => (row.fileId || row.path) === selectedKey) ?? null;
        }
        renderSummary(pageRows);
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
        } else if (pageIsActive && !lastLoadError) {
            refreshTimer = window.setTimeout(refreshFileActivity, POLL_INTERVAL_MS);
        }
    }
}

async function loadCapabilities() {
    const generation = modeGeneration;
    try {
        const capabilities = await getCapabilities();
        if (generation === modeGeneration && !isMockDataEnabled()) {
            reportedCapability = capabilities && Object.hasOwn(capabilities, "file_access_metrics")
                ? capabilities.file_access_metrics
                : null;
        }
    } catch {
        if (generation === modeGeneration) reportedCapability = null;
    }
}

async function changeDataSource() {
    const source = document.getElementById("file-data-source").value;
    setMockDataEnabled(source === "mock");
    modeGeneration += 1;
    const selectedGeneration = modeGeneration;
    reportedCapability = null;
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
    source.addEventListener("change", changeDataSource);
    search.addEventListener("input", renderTable);
    activityFilter.addEventListener("change", renderTable);
    sort.addEventListener("change", renderTable);
    renderSourceStatus();
    renderSummary(null);
    renderTable();

    const initialGeneration = modeGeneration;
    if (!isMockDataEnabled()) await loadCapabilities();
    if (initialGeneration === modeGeneration) await refreshFileActivity();
}

initialize();
window.addEventListener("pagehide", () => {
    pageIsActive = false;
    window.clearTimeout(refreshTimer);
});
