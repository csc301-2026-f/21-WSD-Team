
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

    // Independently collect valid values for each measurement.
    const getValidValues = key =>
        metrics
            .map(metric => metric[key])
            .filter(value =>
                typeof value === "number" &&
                Number.isFinite(value) &&
                value >= 0
            );

    const readBytes = getValidValues("read_bytes_per_sec");
    const writeBytes = getValidValues("write_bytes_per_sec");
    const readIops = getValidValues("read_iops");
    const writeIops = getValidValues("write_iops");
    const readLatencies = getValidValues("avg_read_latency_ms");
    const writeLatencies = getValidValues("avg_write_latency_ms");

    const sum = values =>
        values.reduce((total, value) => total + value, 0);

    const average = values =>
        values.length
            ? `${(sum(values) / values.length).toFixed(2)} ms`
            : "Not provided";

    const formatMBps = value =>
        `${(value / 1_000_000).toFixed(2)} MB/s`;

    const formatIops = value =>
        value.toLocaleString(undefined, {
            maximumFractionDigits: 1
        });

    const totalReadBytes = sum(readBytes);
    const totalWriteBytes = sum(writeBytes);
    const totalReadIops = sum(readIops);
    const totalWriteIops = sum(writeIops);

    document.getElementById("total-throughput").textContent =
        formatMBps(totalReadBytes + totalWriteBytes);

    document.getElementById("read-throughput").textContent =
        formatMBps(totalReadBytes);

    document.getElementById("write-throughput").textContent =
        formatMBps(totalWriteBytes);

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

    document.getElementById("metrics-updated").textContent =
        new Date().toLocaleTimeString();

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
