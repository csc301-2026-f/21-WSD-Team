
import { getDevices, getLatestMetrics } from "./api.js";

import {
    initializeCharts,
    updateMetricsCharts
} from "./charts.js";

import {
    calculateUsedPercent,
    formatMBps,
    formatIops,
    formatAverageLatency,
    getValidMetricValues,
    sumMetricValues
} from "./formatting.js";

// How often to refresh data (milliseconds).
const REFRESH_INTERVAL_MS = 2000;


// ------------------------------
// RENDER STORAGE DRIVE BOXES
// ------------------------------

function renderDrives(devices) {
    const container = document.getElementById("driveContainer");

    if (!container) return;

    // Remove boxes from the previous refresh.
    container.replaceChildren();

    for (const device of devices) {
        const capacity = device.capacity_bytes;
        const free = device.free_bytes;

        const usedPercent = calculateUsedPercent(
            capacity,
            free
        );

        // Create the drive box.
        const box = document.createElement("div");
        box.className = "box";

        // Create the drive heading.
        const title = document.createElement("h3");
        title.className = "drive-title";

        const mount = device.mount_points?.[0];
        const driveName = device.display_name || device.device_id;

        title.textContent = mount
            ? `${mount} Drive - ${driveName}`
            : driveName;

        box.appendChild(title);

        if (usedPercent === null) {
            const label = document.createElement("p");
            label.className = "storage-label";
            label.textContent = "Storage usage unavailable";
            box.appendChild(label);
        } else {
            // Create the outer bar.
            const bar = document.createElement("div");
            bar.className = "storage-bar-container";

            // Create the filled portion.
            const fill = document.createElement("div");
            fill.className = "storage-bar-inner";
            fill.style.width = `${usedPercent}%`;

            bar.appendChild(fill);

            // Display usage percentage below the bar.
            const label = document.createElement("p");
            label.className = "storage-label";
            label.textContent = `${usedPercent.toFixed(1)}% used`;

            box.append(bar, label);
        }

        container.appendChild(box);
    }
}


// ------------------------------
// UPDATE PERFORMANCE STATISTICS
// ------------------------------

function updatePerformanceStats(metrics) {
    if (!Array.isArray(metrics) || metrics.length === 0) {
        return;
    }

    // Independently collect valid values for each measurement.
    const readBytes = getValidMetricValues(
        metrics,
        "read_bytes_per_sec"
    );

    const writeBytes = getValidMetricValues(
        metrics,
        "write_bytes_per_sec"
    );

    const readIops = getValidMetricValues(
        metrics,
        "read_iops"
    );

    const writeIops = getValidMetricValues(
        metrics,
        "write_iops"
    );

    const readLatencies = getValidMetricValues(
        metrics,
        "avg_read_latency_ms"
    );

    const writeLatencies = getValidMetricValues(
        metrics,
        "avg_write_latency_ms"
    );

    // Calculate totals independently.
    const totalReadBytes = sumMetricValues(
        metrics,
        "read_bytes_per_sec"
    );

    const totalWriteBytes = sumMetricValues(
        metrics,
        "write_bytes_per_sec"
    );

    const totalReadIops = sumMetricValues(
        metrics,
        "read_iops"
    );

    const totalWriteIops = sumMetricValues(
        metrics,
        "write_iops"
    );

    // Update throughput displays.
    document.getElementById("total-throughput").textContent =
        formatMBps(totalReadBytes + totalWriteBytes);

    document.getElementById("read-throughput").textContent =
        formatMBps(totalReadBytes);

    document.getElementById("write-throughput").textContent =
        formatMBps(totalWriteBytes);

    // Update IOPS displays.
    document.getElementById("current-iops").textContent =
        formatIops(totalReadIops + totalWriteIops);

    document.getElementById("read-iops").textContent =
        formatIops(totalReadIops);

    document.getElementById("write-iops").textContent =
        formatIops(totalWriteIops);

    // Count devices with at least one valid measurement.
    const reportingDevices = new Set(
        metrics
            .filter(metric =>
                [
                    metric.read_bytes_per_sec,
                    metric.write_bytes_per_sec,
                    metric.read_iops,
                    metric.write_iops
                ].some(value =>
                    typeof value === "number" &&
                    Number.isFinite(value) &&
                    value >= 0
                )
            )
            .map(metric => metric.device_id)
    );

    document.getElementById("devices-reporting").textContent =
        reportingDevices.size;

    // Update timestamp.
    document.getElementById("metrics-updated").textContent =
        new Date().toLocaleTimeString();

    // Update latency displays.
    document.getElementById("read-latency").textContent =
        formatAverageLatency(readLatencies);

    document.getElementById("write-latency").textContent =
        formatAverageLatency(writeLatencies);
}


// ------------------------------
// REFRESH DRIVE DATA
// ------------------------------

async function refreshDrives() {
    try {
        const devices = await getDevices();

        console.log("Devices received:", devices);

        renderDrives(devices);
    } catch (error) {
        console.error("Failed to load drives:", error);
    } finally {
        // Schedule the next refresh after this request finishes.
        setTimeout(refreshDrives, 10000);
    }
}


// ------------------------------
// REFRESH METRICS AND CHARTS
// ------------------------------

async function refreshMetrics() {
    try {
        const metrics = await getLatestMetrics();

        updateMetricsCharts(metrics);
        updatePerformanceStats(metrics);
    } catch (error) {
        console.error("Failed to update metrics charts:", error);
    } finally {
        // Schedule the next refresh after this request finishes.
        setTimeout(refreshMetrics, REFRESH_INTERVAL_MS);
    }
}


// ------------------------------
// START DASHBOARD
// ------------------------------

function startDashboard() {
    // Refresh drives only if this page has a drive container.
    if (document.getElementById("driveContainer")) {
        refreshDrives();
    }

    // Only initialize and refresh charts on the statistics page.
    const hasCharts =
        document.getElementById("throughputChart") &&
        document.getElementById("iopsChart");

    if (hasCharts) {
        initializeCharts();
        refreshMetrics();
    }
}

startDashboard();
