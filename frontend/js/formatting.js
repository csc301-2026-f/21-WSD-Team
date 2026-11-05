// Calculate drive usage as a percentage.
// Returns null when capacity/free-space data is invalid.
export function calculateUsedPercent(capacity, free) {
    const valid =
        typeof capacity === "number" &&
        typeof free === "number" &&
        Number.isFinite(capacity) &&
        Number.isFinite(free) &&
        capacity > 0 &&
        free >= 0 &&
        free <= capacity;

    if (!valid) {
        return null;
    }

    return ((capacity - free) / capacity) * 100;
}


// Convert bytes per second into MB/s.
export function formatMBps(bytesPerSecond) {
    if (
        typeof bytesPerSecond !== "number" ||
        !Number.isFinite(bytesPerSecond) ||
        bytesPerSecond < 0
    ) {
        return "Not provided";
    }

    return `${(bytesPerSecond / 1_000_000).toFixed(2)} MB/s`;
}


// Format an IOPS measurement.
export function formatIops(iops) {
    if (
        typeof iops !== "number" ||
        !Number.isFinite(iops) ||
        iops < 0
    ) {
        return "Not provided";
    }

    return iops.toLocaleString("en-CA", {
        maximumFractionDigits: 1
    });
}


// Calculate and format the average latency.
export function formatAverageLatency(values) {
    const validValues = values.filter(value =>
        typeof value === "number" &&
        Number.isFinite(value) &&
        value >= 0
    );

    if (validValues.length === 0) {
        return "Not provided";
    }

    const total = validValues.reduce(
        (sum, value) => sum + value,
        0
    );

    return `${(total / validValues.length).toFixed(2)} ms`;
}


// Collect valid numeric measurements from metric records.
export function getValidMetricValues(metrics, key) {
    if (!Array.isArray(metrics)) {
        return [];
    }

    return metrics
        .map(metric => metric[key])
        .filter(value =>
            typeof value === "number" &&
            Number.isFinite(value) &&
            value >= 0
        );
}


// Sum valid measurements from metric records.
export function sumMetricValues(metrics, key) {
    return getValidMetricValues(metrics, key)
        .reduce((total, value) => total + value, 0);
}