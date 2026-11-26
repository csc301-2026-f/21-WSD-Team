// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { chartColors, createChartOptions } from "./chartTheme.js";
import { buildFileActivityHistory, rankFileActivity } from "./fileIoHistory.js";

let throughputChart = null;
let operationsChart = null;

function createChart(canvas, datasets, yTitle) {
    const options = createChartOptions({ yTitle, maintainAspectRatio: false });
    return new window.Chart(canvas, {
        type: "line",
        data: { labels: [], datasets: datasets.map(dataset => ({
            ...dataset,
            data: [],
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 3,
            tension: 0.2,
            fill: false,
            spanGaps: false
        })) },
        options
    });
}

export function renderFileActivityHistory(observations, mode = "live") {
    const status = document.getElementById("file-history-status");
    const activeList = document.getElementById("file-history-active-files");
    const throughputCanvas = document.getElementById("file-history-throughput-chart");
    const operationsCanvas = document.getElementById("file-history-operations-chart");
    if (!status || !activeList || !throughputCanvas || !operationsCanvas) return;

    if (!window.Chart) {
        status.textContent = "Chart.js could not be loaded; temporary history is still being collected.";
        return;
    }

    if (!throughputChart) {
        throughputChart = createChart(throughputCanvas, [
            { label: "Read throughput (MB/s)", borderColor: chartColors.navy, backgroundColor: chartColors.navy },
            { label: "Write throughput (MB/s)", borderColor: chartColors.amber, backgroundColor: chartColors.amber },
            { label: "Total file I/O (MB/s)", borderColor: "#43845c", backgroundColor: "#43845c" }
        ], "MB/s");
        operationsChart = createChart(operationsCanvas, [
            { label: "Read operations/s", borderColor: chartColors.navy, backgroundColor: chartColors.navy },
            { label: "Write operations/s", borderColor: chartColors.amber, backgroundColor: chartColors.amber }
        ], "Operations per second");
    }

    const series = buildFileActivityHistory(observations);
    const labels = series.map(point => new Date(point.timestamp).toLocaleTimeString([], {
        minute: "2-digit", second: "2-digit"
    }));
    const toMBps = value => value === null ? null : value / 1_000_000;

    throughputChart.data.labels = labels;
    throughputChart.data.datasets[0].data = series.map(point => toMBps(point.readBytesPerSecond));
    throughputChart.data.datasets[1].data = series.map(point => toMBps(point.writeBytesPerSecond));
    throughputChart.data.datasets[2].data = series.map(point => toMBps(point.totalBytesPerSecond));
    throughputChart.update("none");

    operationsChart.data.labels = labels;
    operationsChart.data.datasets[0].data = series.map(point => point.readOpsPerSecond);
    operationsChart.data.datasets[1].data = series.map(point => point.writeOpsPerSecond);
    operationsChart.update("none");

    activeList.replaceChildren();
    const ranked = rankFileActivity(observations, mode === "mock" ? 50 : 10);
    if (!ranked.length) {
        const item = document.createElement("li");
        item.textContent = "No file activity observations are available yet.";
        activeList.appendChild(item);
    } else {
        for (const file of ranked) {
            const item = document.createElement("li");
            const path = document.createElement("span");
            path.textContent = file.path;
            path.title = file.path;
            const rates = document.createElement("strong");
            rates.textContent = file.averageBytesPerSecond === null
                ? "Throughput unavailable"
                : `${(file.averageBytesPerSecond / 1_000_000).toLocaleString("en-CA", { maximumFractionDigits: 2 })} MB/s avg`;
            item.append(path, rates);
            activeList.appendChild(item);
        }
    }

    const recordCount = observations.reduce((count, observation) => count + observation.rows.length, 0);
    if (!recordCount) {
        status.textContent = mode === "mock"
            ? "No file activity is available in the mock preview."
            : observations.length
            ? "No recent file activity is available."
            : "Collecting file activity. Historical charts will populate as new observations arrive.";
    } else {
        status.textContent = mode === "mock"
            ? `Mock preview activity: ${recordCount} file record(s).`
            : `Recent live activity: ${observations.length} samples and ${recordCount} file record(s).`;
    }
}
