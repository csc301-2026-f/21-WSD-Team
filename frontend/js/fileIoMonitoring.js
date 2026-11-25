// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { getFileIoAvailability, normalizeFileActivity } from "./fileIoApi.js";
import { chartColors, createChartOptions } from "./chartTheme.js";

let pageRows = null;
let selectedFile = null;
let throughputChart = null;
let operationsChart = null;

const valid = value => typeof value === "number" && Number.isFinite(value);
const unavailable = "Unavailable";
const MAX_RENDERED_ROWS = 500;
const fmtBytes = value => {
    if (!valid(value)) return unavailable;
    const units = ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"];
    let amount = value, unit = 0;
    while (amount >= 1000 && unit < units.length - 1) { amount /= 1000; unit++; }
    return `${amount.toLocaleString("en-CA", { maximumFractionDigits: 2 })} ${units[unit]}`;
};
const fmtRate = value => valid(value)
    ? `${value.toLocaleString("en-CA", { maximumFractionDigits: 2 })}/s`
    : unavailable;
const fmtTime = value => {
    const time = Date.parse(value);
    return Number.isFinite(time) ? new Date(time).toLocaleString() : unavailable;
};
const setText = (id, value) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
};

function renderSummary(rows) {
    if (rows === null) {
        for (const id of ["file-total-read", "file-total-write", "file-total-read-ops", "file-total-write-ops", "file-active-count", "file-most-active"]) {
            setText(id, unavailable);
        }
        return;
    }
    const read = rows.map(row => row.readBytesPerSec);
    const write = rows.map(row => row.writeBytesPerSec);
    const readOps = rows.map(row => row.readOpsPerSec);
    const writeOps = rows.map(row => row.writeOpsPerSec);
    const sumKnown = values => values.length === 0
        ? 0
        : values.every(valid) ? values.reduce((total, value) => total + value, 0) : null;
    const active = rows.filter(row =>
        (valid(row.readBytesPerSec) && row.readBytesPerSec > 0) ||
        (valid(row.writeBytesPerSec) && row.writeBytesPerSec > 0) ||
        (valid(row.readOpsPerSec) && row.readOpsPerSec > 0) ||
        (valid(row.writeOpsPerSec) && row.writeOpsPerSec > 0)
    );
    const mostActive = rows.filter(row => valid(row.totalBytesPerSec)).sort((a, b) =>
        (b.totalBytesPerSec ?? -1) - (a.totalBytesPerSec ?? -1)
    )[0];

    setText("file-total-read", fmtBytes(sumKnown(read)));
    setText("file-total-write", fmtBytes(sumKnown(write)));
    setText("file-total-read-ops", fmtRate(sumKnown(readOps)));
    setText("file-total-write-ops", fmtRate(sumKnown(writeOps)));
    setText("file-active-count", rows.length ? String(active.length) : "0");
    setText("file-most-active", mostActive?.path || mostActive?.name || unavailable);
}

function renderDetails(row) {
    const grid = document.getElementById("file-detail-grid");
    grid.replaceChildren();
    if (!row) {
        setText("file-detail-status", "Select a file with reported activity to inspect its details.");
        return;
    }

    setText("file-detail-status", row.path || row.name || "Selected file");
    const details = [
        ["Full path", row.path], ["File name", row.name], ["File ID", row.fileId],
        ["Device", row.deviceId], ["Process", null],
        ["Read throughput", fmtBytes(row.readBytesPerSec)],
        ["Write throughput", fmtBytes(row.writeBytesPerSec)],
        ["Read operations", fmtRate(row.readOpsPerSec)],
        ["Write operations", fmtRate(row.writeOpsPerSec)],
        ["Read bytes in window", row.readBytes], ["Write bytes in window", row.writeBytes],
        ["File size", row.fileSizeBytes], ["Window start", fmtTime(row.windowStartUtc)],
        ["Latest observed window end", fmtTime(row.lastActivity)], ["Measurement source", row.source]
    ];
    for (const [label, value] of details) {
        const item = document.createElement("div");
        item.className = "file-detail-item";
        const heading = document.createElement("span");
        heading.textContent = label;
        const content = document.createElement("strong");
        if (label === "Read bytes in window" || label === "Write bytes in window" || label === "File size") {
            content.textContent = valid(value) ? `${value.toLocaleString("en-CA")} bytes` : unavailable;
        } else {
            content.textContent = value == null ? unavailable : String(value);
        }
        item.append(heading, content);
        grid.appendChild(item);
    }
}

function filteredRows() {
    const query = document.getElementById("file-search").value.trim().toLowerCase();
    const activity = document.getElementById("file-activity-filter").value;
    const sort = document.getElementById("file-sort").value;
    const rows = (pageRows ?? []).filter(row => {
        const matchesQuery = !query || `${row.path ?? ""} ${row.name ?? ""}`.toLowerCase().includes(query);
        const hasRead = valid(row.readBytesPerSec) && row.readBytesPerSec > 0;
        const hasWrite = valid(row.writeBytesPerSec) && row.writeBytesPerSec > 0;
        const matchesActivity = activity === "all" || (activity === "read" ? hasRead : hasWrite);
        return matchesQuery && matchesActivity;
    });
    const valueFor = row => ({
        total: row.totalBytesPerSec,
        read: row.readBytesPerSec,
        write: row.writeBytesPerSec,
        read_ops: row.readOpsPerSec,
        write_ops: row.writeOpsPerSec,
        name: row.name ?? "",
        path: row.path ?? ""
    })[sort];
    rows.sort((a, b) => {
        const left = valueFor(a), right = valueFor(b);
        if (typeof left === "string") return left.localeCompare(right);
        if (left == null) return right == null ? 0 : 1;
        if (right == null) return -1;
        return right - left;
    });
    return rows;
}

function renderTable() {
    const body = document.getElementById("file-activity-body");
    const rows = filteredRows();
    const visibleRows = rows.slice(0, MAX_RENDERED_ROWS);
    body.replaceChildren();
    for (const row of visibleRows) {
        const tr = document.createElement("tr");
        tr.tabIndex = 0;
        tr.setAttribute("role", "button");
        const values = [
            row.path || unavailable,
            row.name || unavailable,
            fmtBytes(row.readBytesPerSec),
            fmtBytes(row.writeBytesPerSec),
            fmtRate(row.readOpsPerSec),
            fmtRate(row.writeOpsPerSec),
            fmtBytes(row.totalBytesPerSec),
            fmtTime(row.lastActivity)
        ];
        for (const value of values) {
            const cell = document.createElement("td");
            cell.textContent = value;
            tr.appendChild(cell);
        }
        const key = row.fileId || row.path;
        if (selectedFile && key === (selectedFile.fileId || selectedFile.path)) tr.classList.add("selected-file-row");
        const select = () => {
            selectedFile = row;
            renderTable();
            renderDetails(row);
            setText("file-history-status", "No file history series is available from the current API.");
        };
        tr.addEventListener("click", select);
        tr.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); }
        });
        body.appendChild(tr);
    }

    if (!rows.length) {
        const tr = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 8;
        cell.textContent = pageRows === null
            ? "No file-level measurements are exposed by the current API."
            : pageRows.length ? "No files match the current search and activity filter." : "No files are reporting activity for this interval.";
        tr.appendChild(cell);
        body.appendChild(tr);
    }
    setText("file-table-status", pageRows === null
        ? "File-level measurements are unavailable."
        : pageRows.length
        ? rows.length > MAX_RENDERED_ROWS
            ? `Showing the first ${MAX_RENDERED_ROWS} of ${rows.length} matching file records (${pageRows.length} total).`
            : `${rows.length} of ${pageRows.length} file record(s) shown.`
        : "No file activity was reported for the current interval.");
}

/** Future API integration entry point for a FileActivity[] response. */
export function renderFileActivity(records) {
    pageRows = normalizeFileActivity(records);
    renderSummary(pageRows);
    renderTable();
}

function initCharts() {
    const throughputCanvas = document.getElementById("file-throughput-chart");
    const opsCanvas = document.getElementById("file-ops-chart");
    if (!window.Chart) {
        setText("file-history-status", "Chart.js is unavailable; file history charts cannot be drawn.");
        return;
    }
    throughputChart = new window.Chart(throughputCanvas, {
        type: "line",
        data: { labels: [], datasets: [
            { label: "Read (MB/s)", data: [], borderColor: chartColors.navy },
            { label: "Write (MB/s)", data: [], borderColor: chartColors.amber }
        ] },
        options: createChartOptions({ yTitle: "Throughput (MB/s)" })
    });
    operationsChart = new window.Chart(opsCanvas, {
        type: "line",
        data: { labels: [], datasets: [
            { label: "Read operations/s", data: [], borderColor: chartColors.navy },
            { label: "Write operations/s", data: [], borderColor: chartColors.amber }
        ] },
        options: createChartOptions({ yTitle: "Operations per second" })
    });
}

/*
 * Future history integration point: pass normalized FileActivity records for
 * one file from a real history endpoint. The current page never calls this
 * with generated or process/device-derived samples.
 */
export function renderFileHistory(records, filePath) {
    if (!throughputChart || !operationsChart || !Array.isArray(records)) return;
    const rows = normalizeFileActivity(records)
        .filter(row => row.path === filePath && row.lastActivity)
        .sort((a, b) => Date.parse(a.lastActivity) - Date.parse(b.lastActivity));
    const labels = rows.map(row => new Date(row.lastActivity).toLocaleTimeString());
    throughputChart.data.labels = labels;
    throughputChart.data.datasets[0].data = rows.map(row => valid(row.readBytesPerSec) ? row.readBytesPerSec / 1_000_000 : null);
    throughputChart.data.datasets[1].data = rows.map(row => valid(row.writeBytesPerSec) ? row.writeBytesPerSec / 1_000_000 : null);
    operationsChart.data.labels = labels;
    operationsChart.data.datasets[0].data = rows.map(row => row.readOpsPerSec);
    operationsChart.data.datasets[1].data = rows.map(row => row.writeOpsPerSec);
    throughputChart.update("none");
    operationsChart.update("none");
}

async function initialize() {
    initCharts();
    document.getElementById("file-search").addEventListener("input", renderTable);
    document.getElementById("file-activity-filter").addEventListener("change", renderTable);
    document.getElementById("file-sort").addEventListener("change", renderTable);
    renderSummary(null);
    renderTable();

    try {
        const availability = await getFileIoAvailability();
        if (availability.reportedCapability === true) {
            setText("file-io-status", "The backend reports file access capability, but no file activity HTTP endpoint is exposed, so this page cannot retrieve file measurements.");
        } else if (availability.reportedCapability === false) {
            setText("file-io-status", "The backend reports file access metrics as unavailable, and no file activity HTTP endpoint is exposed.");
        } else {
            setText("file-io-status", "The backend did not report file access capability, and no file activity HTTP endpoint is exposed.");
        }
    } catch (error) {
        setText("file-io-status", `Could not load backend capabilities: ${error.message}. File measurements remain unavailable.`);
    }
}

initialize();
window.addEventListener("pagehide", () => {
    throughputChart?.destroy();
    operationsChart?.destroy();
});
