// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only

import {
    getLatestProcesses,
    getProcessHistory
} from "./api.js";

import {
    getProcessInstanceId
} from "./processUtils.js";

const REFRESH_INTERVAL_MS = 2000;
const HISTORY_WINDOW_MS = 60 * 1000;

const processSelect = document.getElementById("history-process-select");
const statusElement = document.getElementById("history-status");
const canvas = document.getElementById("processHistoryChart");

let historyChart = null;
let isRefreshing = false;
let refreshRequested = false;
let refreshTimer = null;

// Preserve the selected process independently of the latest process list.
let selectedProcessInstanceId = null;

function getProcessOptionValue(processInstanceId) {
    return JSON.stringify({
        process_instance_id: processInstanceId
    });
}

function getSelectedProcessId() {
    if (!processSelect.value) {
        return null;
    }

    try {
        const selected = JSON.parse(processSelect.value);
        return selected.process_instance_id ?? null;
    } catch {
        return null;
    }
}

function formatTime(timestamp) {
    if (!timestamp) return "Not available";

    const date = new Date(timestamp);

    return Number.isNaN(date.getTime())
        ? "Not available"
        : date.toLocaleTimeString();
}

function formatRate(value) {
    if (value === null || value === undefined) {
        return null;
    }

    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return null;
    }

    return numericValue / 1_000_000;
}

/* PROCESS SELECTOR */

function populateProcessSelect(processes) {
    const previousId =
        selectedProcessInstanceId ?? getSelectedProcessId();

    const uniqueProcesses = new Map();

    for (const process of processes) {
        const processInstanceId = getProcessInstanceId(process);
        uniqueProcesses.set(processInstanceId, process);
    }

    processSelect.replaceChildren();

    for (const [processInstanceId, process] of uniqueProcesses) {
        const option = document.createElement("option");

        option.value = getProcessOptionValue(processInstanceId);

        option.textContent =
            `${process.process_name ?? "Unknown"} (PID ${process.pid})`;

        processSelect.appendChild(option);
    }

    if (previousId !== null) {
        const matchingOption = [...processSelect.options].find(
            option => {
                const value = JSON.parse(option.value);

                return value.process_instance_id === previousId;
            }
        );

        if (!matchingOption) {
            const pid = previousId.split("_", 1)[0];

            const option = document.createElement("option");

            option.value = getProcessOptionValue(previousId);
            option.textContent =
                `PID ${pid} (not currently reporting I/O)`;

            processSelect.appendChild(option);
        }

        processSelect.value = getProcessOptionValue(previousId);
        selectedProcessInstanceId = previousId;

    } else if (processSelect.options.length > 0) {
        // Select the first process only on initial load.
        processSelect.selectedIndex = 0;
        selectedProcessInstanceId = getSelectedProcessId();

    } else {
        selectedProcessInstanceId = null;
    }
}

/* CHART RENDERING */

function renderHistory(records) {
    const labels = records.map(record =>
        formatTime(record.timestamp_utc)
    );

    const readRates = records.map(record =>
        formatRate(record.read_bytes_per_sec)
    );

    const writeRates = records.map(record =>
        formatRate(record.write_bytes_per_sec)
    );

    if (!historyChart) {
        historyChart = new window.Chart(canvas, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Read (MB/s)",
                        data: readRates,
                        borderColor: "#0D9488",
                        backgroundColor: "#0D9488",
                        tension: 0.2,
                        spanGaps: false
                    },
                    {
                        label: "Write (MB/s)",
                        data: writeRates,
                        borderColor: "#D97706",
                        backgroundColor: "#D97706",
                        tension: 0.2,
                        spanGaps: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    intersect: false,
                    mode: "index"
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Time"
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Throughput (MB/s)"
                        }
                    }
                }
            }
        });

        return;
    }

    historyChart.data.labels = labels;
    historyChart.data.datasets[0].data = readRates;
    historyChart.data.datasets[1].data = writeRates;

    historyChart.update("none");
}

/* HISTORY REFRESH */

async function refreshHistory() {
    if (isRefreshing) {
        refreshRequested = true;
        return;
    }

    isRefreshing = true;

    try {
        const processes = await getLatestProcesses();

        if (!Array.isArray(processes)) {
            throw new Error("Expected an array of process records.");
        }

        populateProcessSelect(processes);

        const selectedValue = processSelect.value;

        if (!selectedValue) {
            statusElement.textContent = "No processes available.";
            renderHistory([]);
            return;
        }

        const selectedProcess = JSON.parse(selectedValue);

        selectedProcessInstanceId =
            selectedProcess.process_instance_id;

        const end = new Date();
        const start = new Date(
            end.getTime() - HISTORY_WINDOW_MS
        );

        const records = await getProcessHistory({
            process_instance_id:
                selectedProcess.process_instance_id,
            start_utc: start.toISOString(),
            end_utc: end.toISOString()
        });

        if (!Array.isArray(records)) {
            throw new Error(
                "Expected an array of process history records."
            );
        }

        renderHistory(records);

        statusElement.textContent = records.length === 0
            ? "No history samples found for this process in the last minute."
            : `${records.length} samples · Last 1 minute · Updated ${formatTime(end)}`;

    } catch (error) {
        console.error("Failed to load process history:", error);

        statusElement.textContent =
            "Unable to load process history. Retrying...";

    } finally {
        isRefreshing = false;

        if (refreshRequested) {
            refreshRequested = false;
            refreshHistory();
        } else {
            refreshTimer = setTimeout(
                refreshHistory,
                REFRESH_INTERVAL_MS
            );
        }
    }
}

/* INITIALIZATION AND EVENT LISTENERS */

if (!processSelect || !statusElement || !canvas) {
    console.error(
        "Process history page is missing required HTML elements."
    );
} else if (!window.Chart) {
    statusElement.textContent =
        "Chart.js could not be loaded.";

    console.error("Chart.js is unavailable.");

} else {
    processSelect.addEventListener("change", () => {
        selectedProcessInstanceId = getSelectedProcessId();

        if (refreshTimer !== null) {
            clearTimeout(refreshTimer);
            refreshTimer = null;
        }

        refreshHistory();
    });

    // Allow the process table to control the history graph selection.
    document.addEventListener(
        "process-selected-for-history",
        event => {
            const selectedId = event.detail?.process_instance_id;

            if (!selectedId) return;

            selectedProcessInstanceId = selectedId;

            const matchingOption = [...processSelect.options].find(
                option => {
                    const value = JSON.parse(option.value);

                    return value.process_instance_id === selectedId;
                }
            );

            if (matchingOption) {
                processSelect.value = matchingOption.value;
            } else {
                const option = document.createElement("option");

                option.value = getProcessOptionValue(selectedId);
                option.textContent =
                    `PID ${selectedId.split("_", 1)[0]}`;

                processSelect.appendChild(option);
                processSelect.value = option.value;
            }

            if (refreshTimer !== null) {
                clearTimeout(refreshTimer);
                refreshTimer = null;
            }

            refreshHistory();
        }
    );

    refreshHistory();
}
