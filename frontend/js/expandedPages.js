// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { getDevices, getLatestMetrics, getLatestProcesses, getProcessHistory, getRecommendations } from "./api.js";
import { getProcessInstanceId } from "./processUtils.js";
import { chartColors, createChartOptions } from "./chartTheme.js";

const page = location.pathname.split("/").pop();
const latest = { devices: [], metrics: [], processes: [], recommendations: [], updated: null };
const valid = value => typeof value === "number" && Number.isFinite(value) && value >= 0;
const number = value => valid(value) ? value : null;
const fmtBytes = value => {
    if (!valid(value)) return "Unavailable";
    const units = ["B", "KB", "MB", "GB", "TB", "PB"];
    let n = value, i = 0;
    while (n >= 1000 && i < units.length - 1) { n /= 1000; i++; }
    return `${n.toFixed(i ? 2 : 0)} ${units[i]}`;
};
const fmtRate = value => valid(value) ? `${fmtBytes(value)}/s` : "Unavailable";
const fmtIops = value => valid(value) ? value.toLocaleString("en-CA", { maximumFractionDigits: 1 }) : "Unavailable";
const fmtLatency = value => valid(value) ? `${value.toFixed(2)} ms` : "Unavailable";
const fmtPct = value => valid(value) ? `${value.toFixed(1)}%` : "Unavailable";
const sampleStatus = process => {
    const time = Date.parse(process.timestamp_utc);
    if (!Number.isFinite(time)) return "Timestamp unavailable";
    const age = Math.max(0, Date.now() - time);
    const staleAfter = Math.max(30_000, (valid(process.sample_window_seconds) ? process.sample_window_seconds : 0) * 3_000);
    const ageLabel = age < 60_000 ? `${Math.floor(age / 1000)}s ago` : `${Math.floor(age / 60_000)}m ago`;
    return age > staleAfter ? `${ageLabel} · stale` : ageLabel;
};
const sum = (rows, key) => {
    const nums = rows.map(row => number(row?.[key])).filter(v => v !== null);
    return nums.length ? nums.reduce((a, b) => a + b, 0) : null;
};
const keyOf = device => String(device.device_id);
const nameOf = device => device.display_name || device.mount_points?.join(", ") || `Device ${device.device_id}`;
const metricsByDevice = () => new Map(latest.metrics.map(metric => [String(metric.device_id), metric]));
const setText = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
const makeCell = (row, value) => { const td = document.createElement("td"); td.textContent = value == null ? "Unavailable" : String(value); row.appendChild(td); };
const setError = (id, error, prefix) => setText(id, `${prefix} ${error?.message || "Request failed."}`);

async function requestData({ devices = false, metrics = false, processes = false, recommendations = false } = {}) {
    const work = [];
    if (devices) work.push(getDevices().then(data => { latest.devices = Array.isArray(data) ? data : []; }));
    if (metrics) work.push(getLatestMetrics().then(data => { latest.metrics = Array.isArray(data) ? data : []; }));
    if (processes) work.push(getLatestProcesses().then(data => { latest.processes = Array.isArray(data) ? data : []; }));
    if (recommendations) work.push(getRecommendations().then(data => { latest.recommendations = Array.isArray(data) ? data : []; }));
    const results = await Promise.allSettled(work);
    latest.updated = new Date();
    return results.filter(item => item.status === "rejected").map(item => item.reason);
}

function renderOverview(errors) {
    const metrics = latest.metrics, processes = latest.processes;
    setText("overview-drive-count", latest.devices.length.toLocaleString());
    const capacities = latest.devices.map(d => number(d.capacity_bytes)).filter(v => v !== null);
    setText("overview-capacity", capacities.length ? fmtBytes(capacities.reduce((a, b) => a + b, 0)) : "Unavailable");
    setText("overview-read", fmtRate(sum(metrics, "read_bytes_per_sec")));
    setText("overview-write", fmtRate(sum(metrics, "write_bytes_per_sec")));
    const readIops = sum(metrics, "read_iops"), writeIops = sum(metrics, "write_iops");
    setText("overview-iops", readIops === null && writeIops === null ? "Unavailable" : fmtIops((readIops || 0) + (writeIops || 0)));
    setText("overview-processes", processes.length.toLocaleString());
    const list = document.getElementById("overview-drive-list");
    list.replaceChildren();
    for (const d of latest.devices) {
        const tile = document.createElement("article"); tile.className = "metric-tile";
        const h = document.createElement("h2"); h.textContent = nameOf(d);
        const p = document.createElement("p");
        const capacity = number(d.capacity_bytes), free = number(d.free_bytes);
        p.textContent = capacity !== null && free !== null && capacity > 0 ? `${fmtPct((capacity - free) / capacity * 100)} used · ${fmtBytes(free)} available` : "Capacity usage unavailable";
        tile.append(h, p); list.appendChild(tile);
    }
    if (!latest.devices.length) list.textContent = "No drives are currently reported.";
    const warnings = latest.devices.filter(d => {
        const capacity = number(d.capacity_bytes), free = number(d.free_bytes);
        return capacity !== null && free !== null && capacity > 0 && (capacity - free) / capacity >= 0.9;
    });
    setText("overview-alerts", warnings.length ? `Capacity warning: ${warnings.map(nameOf).join(", ")} at or above 90% utilized.` : errors.length ? "Could not evaluate drive capacity because some data is unavailable." : "No monitored drives are at or above 90% utilization.");
    setText("overview-updated", latest.updated ? `Latest API responses received at ${latest.updated.toLocaleTimeString()}.` : "Waiting for first update.");
    setText("overview-status", errors.length ? `Some data could not be loaded: ${errors.map(e => e.message).join("; ")}` : "Data refreshed successfully.");
}

function renderDrives(errors) {
    const body = document.getElementById("drives-body"), metricMap = metricsByDevice();
    body.replaceChildren();
    latest.devices.forEach(device => {
        const row = document.createElement("tr"); row.tabIndex = 0; row.setAttribute("role", "button");
        const metric = metricMap.get(keyOf(device)) || {};
        const capacity = number(device.capacity_bytes), free = number(device.free_bytes);
        const used = capacity !== null && free !== null && capacity >= free ? capacity - free : null;
        const pct = capacity && used !== null ? used / capacity * 100 : null;
        [nameOf(device), device.device_id, device.media_type || "Unavailable", fmtBytes(capacity), fmtBytes(used), fmtBytes(free), fmtPct(pct), fmtRate(metric.read_bytes_per_sec), fmtRate(metric.write_bytes_per_sec), fmtIops(metric.read_iops), fmtIops(metric.write_iops), `${fmtLatency(metric.avg_read_latency_ms)} / ${fmtLatency(metric.avg_write_latency_ms)}`].forEach(value => makeCell(row, value));
        if (pct !== null && pct >= 90) row.cells[6].classList.add("drive-warning");
        const show = () => {
            const detail = [
                `Device: ${device.device_id}`, `Host: ${device.host_id ?? "Unavailable"}`, `Name: ${nameOf(device)}`,
                `Type: ${device.media_type ?? "Unavailable"}`, `Mount points: ${device.mount_points?.join(", ") || "Unavailable"}`,
                `Available: ${device.is_available === true ? "Yes" : device.is_available === false ? "No" : "Unavailable"}`,
                `Read latency: ${fmtLatency(metric.avg_read_latency_ms)}`, `Write latency: ${fmtLatency(metric.avg_write_latency_ms)}`
            ]; setText("drive-detail", detail.join(" · "));
        };
        row.addEventListener("click", show); row.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(); } });
        body.appendChild(row);
    });
    if (!latest.devices.length) { const tr = document.createElement("tr"); makeCell(tr, errors.length ? "Unable to load drives." : "No drives reported."); body.appendChild(tr); }
    setText("drives-status", errors.length ? `Some data could not be loaded: ${errors.map(e => e.message).join("; ")}` : `${latest.devices.length} drive(s) · Updated ${latest.updated.toLocaleTimeString()}.`);
}

let driveChart, chartSamples = [], paused = false;
function startAnalytics() {
    const canvas = document.getElementById("drive-performance-chart");
    const select = document.getElementById("analytics-drive");
    if (window.Chart && canvas) driveChart = new Chart(canvas, { type: "line", data: { labels: [], datasets: [] }, options: createChartOptions({ yTitle: "Throughput (MB/s)" }) });
    document.getElementById("analytics-pause").addEventListener("click", event => { paused = !paused; event.currentTarget.textContent = paused ? "Resume updates" : "Pause updates"; });
    select.addEventListener("change", () => updateAnalyticsChart());
}
function updateAnalyticsChart() {
    if (!driveChart) return;
    const selected = document.getElementById("analytics-drive").value;
    const devices = latest.devices.filter(d => !selected || keyOf(d) === selected);
    const palette = [chartColors.navy, "#426f8a", "#68869a", "#8ba1af", "#a8b7c0"];
    const datasets = devices.flatMap((d, i) => [
        { label: `${nameOf(d)} read`, data: chartSamples.map(sample => sample.values[keyOf(d)]?.read ?? null), borderColor: palette[i % palette.length], pointRadius: 0, tension: .2, spanGaps: true },
        { label: `${nameOf(d)} write`, data: chartSamples.map(sample => sample.values[keyOf(d)]?.write ?? null), borderColor: palette[i % palette.length], borderDash: [5, 4], pointRadius: 0, tension: .2, spanGaps: true }
    ]);
    driveChart.data.labels = chartSamples.map(s => s.label); driveChart.data.datasets = datasets; driveChart.update("none");
}
function renderAnalytics(errors) {
    const select = document.getElementById("analytics-drive"), old = select.value;
    select.replaceChildren(new Option("All reporting drives", ""));
    latest.devices.forEach(d => select.add(new Option(nameOf(d), keyOf(d))));
    if ([...select.options].some(o => o.value === old)) select.value = old;
    const map = metricsByDevice(), body = document.getElementById("analytics-body"); body.replaceChildren();
    latest.devices.forEach(d => {
        const m = map.get(keyOf(d)) || {}, row = document.createElement("tr");
        [nameOf(d), fmtRate(m.read_bytes_per_sec), fmtRate(m.write_bytes_per_sec), fmtIops(m.read_iops), fmtIops(m.write_iops), fmtLatency(m.avg_read_latency_ms), fmtLatency(m.avg_write_latency_ms), m.timestamp_utc ? new Date(m.timestamp_utc).toLocaleTimeString() : "Unavailable"].forEach(v => makeCell(row, v)); body.appendChild(row);
    });
    if (!latest.devices.length) { const row = document.createElement("tr"); makeCell(row, "No devices reported."); body.appendChild(row); }
    const values = {};
    for (const d of latest.devices) {
        const m = map.get(keyOf(d)) || {};
        values[keyOf(d)] = { read: valid(m.read_bytes_per_sec) ? m.read_bytes_per_sec / 1e6 : null, write: valid(m.write_bytes_per_sec) ? m.write_bytes_per_sec / 1e6 : null };
    }
    chartSamples.push({ label: latest.updated.toLocaleTimeString(), values }); chartSamples = chartSamples.slice(-60);
    updateAnalyticsChart();
    setText("analytics-status", errors.length ? `Could not load some data: ${errors.map(e => e.message).join("; ")}` : `Latest measurements received ${latest.updated.toLocaleTimeString()}.`);
}

let processChart, selectedProcess = null, processTimer = null, historyRequest = false, pendingHistoryProcess = null;
function renderProcessAnalytics(errors = []) {
    const body = document.getElementById("process-analytics-body"), query = document.getElementById("process-analytics-search").value.trim().toLowerCase();
    const sort = document.getElementById("process-sort").value;
    let rows = latest.processes.filter(p => `${p.process_name ?? ""} ${p.pid ?? ""}`.toLowerCase().includes(query));
    const rate = value => number(value) ?? -1;
    rows.sort((a, b) => sort === "name" ? String(a.process_name || "").localeCompare(String(b.process_name || "")) : sort === "pid" ? (a.pid || 0) - (b.pid || 0) : sort === "read" ? rate(b.read_bytes_per_sec) - rate(a.read_bytes_per_sec) : sort === "write" ? rate(b.write_bytes_per_sec) - rate(a.write_bytes_per_sec) : (rate(b.read_bytes_per_sec) + rate(b.write_bytes_per_sec)) - (rate(a.read_bytes_per_sec) + rate(a.write_bytes_per_sec)));
    body.replaceChildren();
    rows.forEach(p => {
        const tr = document.createElement("tr"); tr.tabIndex = 0; tr.setAttribute("role", "button");
        [p.process_name || "Unknown", p.pid ?? "Unavailable", fmtRate(p.read_bytes_per_sec), fmtRate(p.write_bytes_per_sec), fmtRate(number(p.read_bytes_per_sec) !== null && number(p.write_bytes_per_sec) !== null ? p.read_bytes_per_sec + p.write_bytes_per_sec : null), p.attributed_device_id ?? "Unattributed", sampleStatus(p)].forEach(v => makeCell(tr, v));
        const select = () => { selectedProcess = p; loadProcessHistory(p); };
        tr.addEventListener("click", select); tr.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(); } }); body.appendChild(tr);
    });
    if (!rows.length) { const tr = document.createElement("tr"); makeCell(tr, latest.processes.length ? "No processes match this search." : "No process measurements are available."); body.appendChild(tr); }
    setText("process-analytics-status", errors.length ? `Process data unavailable: ${errors.map(e => e.message).join("; ")}` : `${rows.length} of ${latest.processes.length} process(es) shown · Updated ${latest.updated.toLocaleTimeString()}.`);
}
function initProcessChart() {
    const canvas = document.getElementById("process-analytics-chart"); if (!window.Chart || !canvas) return;
    processChart = new Chart(canvas, { type: "line", data: { labels: [], datasets: [{ label: "Read (MB/s)", data: [], borderColor: chartColors.navy, pointRadius: 0, pointHoverRadius: 3, tension: .2, fill: false }, { label: "Write (MB/s)", data: [], borderColor: chartColors.amber, pointRadius: 0, pointHoverRadius: 3, tension: .2, fill: false }] }, options: createChartOptions({ yTitle: "Throughput (MB/s)" }) });
}
async function loadProcessHistory(process) {
    if (!processChart) { setText("process-history-status", "Chart.js is unavailable; process history cannot be drawn."); return; }
    if (historyRequest) { pendingHistoryProcess = process; return; }
    historyRequest = true;
    setText("process-history-status", `Loading recent history for ${process.process_name || "Unknown"} (PID ${process.pid})…`);
    const end = new Date(), start = new Date(end.getTime() - 5 * 60 * 1000);
    try {
        const records = await getProcessHistory({ process_instance_id: getProcessInstanceId(process), start_utc: start.toISOString(), end_utc: end.toISOString() });
        if (!Array.isArray(records)) throw new Error("Unexpected history response.");
        if (selectedProcess !== process) return;
        processChart.data.labels = records.map(r => r.timestamp_utc ? new Date(r.timestamp_utc).toLocaleTimeString() : "Unknown");
        processChart.data.datasets[0].data = records.map(r => valid(r.read_bytes_per_sec) ? r.read_bytes_per_sec / 1e6 : null);
        processChart.data.datasets[1].data = records.map(r => valid(r.write_bytes_per_sec) ? r.write_bytes_per_sec / 1e6 : null);
        processChart.update("none"); setText("process-history-status", records.length ? `${records.length} samples returned for the last five minutes.` : "No history samples are available for this process in the last five minutes.");
    } catch (e) { setText("process-history-status", `History unavailable: ${e.message}`); }
    finally {
        historyRequest = false;
        if (pendingHistoryProcess) {
            const next = pendingHistoryProcess;
            pendingHistoryProcess = null;
            if (selectedProcess === next) loadProcessHistory(next);
        }
    }
}

function csvCell(value) { const s = value == null ? "" : String(value); return `"${s.replaceAll('"', '""')}"`; }
function downloadCsv(filename, rows) {
    if (!rows.length) { setText("export-status", "No records are available for this export."); return; }
    const headers = [...new Set(rows.flatMap(row => Object.keys(row)))];
    const csv = [headers.map(csvCell).join(","), ...rows.map(row => headers.map(h => csvCell(row[h])).join(","))].join("\r\n");
    const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a"); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);
    setText("export-status", `Downloaded ${filename} (${rows.length} row(s)).`);
}
function initExport(errors = []) {
    const status = document.getElementById("export-status");
    document.querySelectorAll("[data-export]").forEach(button => button.addEventListener("click", () => {
        const metricMap = metricsByDevice();
        const drives = latest.devices.map(d => { const m = metricMap.get(keyOf(d)) || {}; return { device_id: d.device_id, host_id: d.host_id, display_name: d.display_name, media_type: d.media_type, capacity_bytes: d.capacity_bytes, free_bytes: d.free_bytes, read_bytes_per_sec: m.read_bytes_per_sec, write_bytes_per_sec: m.write_bytes_per_sec, read_iops: m.read_iops, write_iops: m.write_iops, avg_read_latency_ms: m.avg_read_latency_ms, avg_write_latency_ms: m.avg_write_latency_ms, timestamp_utc: m.timestamp_utc }; });
        const type = button.dataset.export;
        if (type === "drives") downloadCsv("wsd-drives.csv", drives);
        else if (type === "processes") downloadCsv("wsd-processes.csv", latest.processes);
        else if (type === "recommendations") downloadCsv("wsd-recommendations.csv", latest.recommendations);
        else downloadCsv("wsd-current-snapshot.csv", [...drives, ...latest.processes.map(p => ({ record_type: "process", ...p })), ...latest.recommendations.map(r => ({ record_type: "recommendation", ...r }))]);
    }));
    const loaded = `Loaded ${latest.devices.length} drives, ${latest.processes.length} processes, and ${latest.recommendations.length} recommendations at ${latest.updated.toLocaleTimeString()}.`;
    setText("export-status", errors.length ? `${loaded} Some sources failed: ${errors.map(e => e.message).join("; ")}` : loaded);
}

async function refresh() {
    let options;
    if (page === "overview.html") options = { devices: true, metrics: true, processes: true };
    else if (page === "drives.html" || page === "analytics.html") options = { devices: true, metrics: true };
    else if (page === "process_analytics.html") options = { processes: true };
    else if (page === "export.html") options = { devices: true, metrics: true, processes: true, recommendations: true };
    else return;
    const errors = await requestData(options);
    if (page === "overview.html") renderOverview(errors);
    if (page === "drives.html") renderDrives(errors);
    if (page === "analytics.html") renderAnalytics(errors);
    if (page === "process_analytics.html") renderProcessAnalytics(errors);
    if (page === "export.html") initExport(errors);
    if (page === "process_analytics.html" && selectedProcess) loadProcessHistory(selectedProcess);
    const delay = page === "analytics.html" ? 3000 : page === "drives.html" ? 10000 : 5000;
    if (page !== "export.html") processTimer = setTimeout(() => { if (!(page === "analytics.html" && paused)) refresh(); else processTimer = setTimeout(refresh, delay); }, delay);
}

if (page === "overview.html" || page === "drives.html" || page === "analytics.html" || page === "process_analytics.html" || page === "export.html") {
    if (page === "analytics.html") startAnalytics();
    if (page === "process_analytics.html") {
        initProcessChart();
        document.getElementById("process-analytics-search").addEventListener("input", renderProcessAnalytics);
        document.getElementById("process-sort").addEventListener("change", renderProcessAnalytics);
    }
    refresh();
    window.addEventListener("pagehide", () => { if (processTimer) clearTimeout(processTimer); });
}
