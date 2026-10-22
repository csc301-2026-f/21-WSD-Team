
import { getDevices, getLatestMetrics } from "./api.js";
import {
    initializeCharts,
    updateMetricsCharts
} from "./charts.js";

// How often to refresh data (milliseconds).
const REFRESH_INTERVAL_MS = 2000;

// ------------------------------
// RENDER STORAGE DRIVE BOXES
// ------------------------------

function renderDrives(devices) {
    const container = document.getElementById("driveContainer");

    // Remove boxes from the previous refresh.
    container.replaceChildren();

    for (const device of devices) {
        const capacity = device.capacity_bytes;
        const free = device.free_bytes;

        const hasUsageData =
            typeof capacity === "number" &&
            typeof free === "number" &&
            Number.isFinite(capacity) &&
            Number.isFinite(free) &&
            capacity > 0 &&
            free >= 0 &&
            free <= capacity;

        const usedPercent = hasUsageData
            ? ((capacity - free) / capacity) * 100
            : null;

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


function updatePerformanceStats(metrics) {
    if (!Array.isArray(metrics) || metrics.length === 0) {
        return;
    }

    // Only include records with numeric measurements.
    const validMetrics = metrics.filter(metric =>
        Number.isFinite(metric.read_bytes_per_sec) &&
        Number.isFinite(metric.write_bytes_per_sec) &&
        Number.isFinite(metric.read_iops) &&
        Number.isFinite(metric.write_iops)
    );

    if (validMetrics.length === 0) {
        return;
    }

    const totalReadBytes = validMetrics.reduce(
        (sum, metric) => sum + metric.read_bytes_per_sec, 0
    );

    const totalWriteBytes = validMetrics.reduce(
        (sum, metric) => sum + metric.write_bytes_per_sec, 0
    );

    const totalReadIops = validMetrics.reduce(
        (sum, metric) => sum + metric.read_iops, 0
    );

    const totalWriteIops = validMetrics.reduce(
        (sum, metric) => sum + metric.write_iops, 0
    );

    // Convert bytes per second to MB/s (decimal units).
    const readMBps = totalReadBytes / 1_000_000;
    const writeMBps = totalWriteBytes / 1_000_000;

    const formatMBps = value => `${value.toFixed(2)} MB/s`;
    const formatIops = value => value.toLocaleString(
        undefined, { maximumFractionDigits: 1 }
    );

    document.getElementById("total-throughput").textContent =
        formatMBps(readMBps + writeMBps);

    document.getElementById("read-throughput").textContent =
        formatMBps(readMBps);

    document.getElementById("write-throughput").textContent =
        formatMBps(writeMBps);

    document.getElementById("current-iops").textContent =
        formatIops(totalReadIops + totalWriteIops);

    document.getElementById("read-iops").textContent =
        formatIops(totalReadIops);

    document.getElementById("write-iops").textContent =
        formatIops(totalWriteIops);

    document.getElementById("devices-reporting").textContent =
        `${validMetrics.length}`;

    const timestamp = new Date().toLocaleTimeString();

    document.getElementById("metrics-updated").textContent =
        timestamp;

    // Average latency across records that provide numeric latency values.
    const readLatencies = validMetrics
        .map(metric => metric.avg_read_latency_ms)
        .filter(value => typeof value === "number" && Number.isFinite(value));

    const writeLatencies = validMetrics
        .map(metric => metric.avg_write_latency_ms)
        .filter(value => typeof value === "number" && Number.isFinite(value));

    const average = values =>
        values.length
            ? `${(values.reduce((sum, value) => sum + value, 0) /
                values.length).toFixed(2)} ms`
            : "Not provided";

    document.getElementById("read-latency").textContent =
        average(readLatencies);

    document.getElementById("write-latency").textContent =
        average(writeLatencies);
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
