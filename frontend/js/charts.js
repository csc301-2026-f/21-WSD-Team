// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { chartColors, createChartOptions } from "./chartTheme.js";

const WINDOW_MS = 5 * 60 * 1000;

// Recent measurements are stored temporarily in browser memory.
const samples = [];

let throughputChart;
let iopsChart;

function average(values) {
    const valid = values.filter(
        value => typeof value === "number" && Number.isFinite(value)
    );

    if (valid.length === 0) return null;

    return valid.reduce((sum, value) => sum + value, 0) / valid.length;
}

function createChart(canvasId, title, datasets, yTitle) {
    const canvas = document.getElementById(canvasId);
    const options = createChartOptions({ yTitle, maintainAspectRatio: true });

    return new Chart(canvas, {
        type: "line",
        data: {
            labels: [],
            datasets: datasets.map(dataset => ({
                label: dataset.label,
                data: [],
                borderColor: dataset.color,
                backgroundColor: dataset.color,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 3,
                tension: 0.2,
                fill: false,
                spanGaps: true
            }))
        },
        options: {
            ...options,
            plugins: {
                ...options.plugins,
                title: { display: false, text: title }
            }
        }
    });
}

export function initializeCharts() {
    throughputChart = createChart(
        "throughputChart",
        "Average Throughput",
        [
            { label: "Read (MB/s)", color: chartColors.navy },
            { label: "Write (MB/s)", color: chartColors.amber }
        ],
        "Throughput (MB/s)"
    );

    iopsChart = createChart(
        "iopsChart",
        "Average IOPS",
        [
            { label: "Read IOPS", color: chartColors.navy },
            { label: "Write IOPS", color: chartColors.amber }
        ],
        "Operations per second"
    );
}

export function updateMetricsCharts(metrics) {
    if (!throughputChart || !iopsChart) {
        initializeCharts();
    }

    if (!Array.isArray(metrics)) {
        throw new Error("Expected an array of device metrics");
    }

    const now = Date.now();

    // Average the current measurements across devices.
    const sample = {
        timestamp: now,
        readMBps: average(
            metrics.map(m => m.read_bytes_per_sec)
                .filter(v => v == null || Number.isFinite(v))
                .map(v => v == null ? null : v / 1_000_000)
        ),
        writeMBps: average(
            metrics.map(m => m.write_bytes_per_sec)
                .filter(v => v == null || Number.isFinite(v))
                .map(v => v == null ? null : v / 1_000_000)
        ),
        readIOPS: average(metrics.map(m => m.read_iops)),
        writeIOPS: average(metrics.map(m => m.write_iops))
    };

    samples.push(sample);

    // Keep enough samples to calculate the rolling five-minute window.
    while (
        samples.length > 0 &&
        samples[0].timestamp < now - WINDOW_MS
    ) {
        samples.shift();
    }

    const labels = [];
    const readMBps = [];
    const writeMBps = [];
    const readIOPS = [];
    const writeIOPS = [];

    // For each point, calculate the average over the preceding five minutes.
    for (const point of samples) {
        const windowSamples = samples.filter(
            s => s.timestamp <= point.timestamp &&
                 s.timestamp >= point.timestamp - WINDOW_MS
        );

        labels.push(
            new Date(point.timestamp).toLocaleTimeString([], {
                minute: "2-digit",
                second: "2-digit"
            })
        );

        readMBps.push(average(windowSamples.map(s => s.readMBps)));
        writeMBps.push(average(windowSamples.map(s => s.writeMBps)));
        readIOPS.push(average(windowSamples.map(s => s.readIOPS)));
        writeIOPS.push(average(windowSamples.map(s => s.writeIOPS)));
    }

    throughputChart.data.labels = labels;
    throughputChart.data.datasets[0].data = readMBps;
    throughputChart.data.datasets[1].data = writeMBps;
    throughputChart.update("none");

    iopsChart.data.labels = labels;
    iopsChart.data.datasets[0].data = readIOPS;
    iopsChart.data.datasets[1].data = writeIOPS;
    iopsChart.update("none");
}
