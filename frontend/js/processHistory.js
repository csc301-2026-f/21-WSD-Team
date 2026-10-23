// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only

import { getLatestProcesses, getProcessHistory } from "./api.js";

const REFRESH_INTERVAL_MS = 2000;
const HISTORY_WINDOW_MS = 60 * 1000;

const processSelect = document.getElementById("history-process-select");
const statusElement = document.getElementById("history-status");
const canvas = document.getElementById("processHistoryChart");

let historyChart = null;
let isRefreshing = false;

function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString();
}

// Identify a process using the documented ProcessMetric fields.
function getProcessKey(process) {
    return `${process.host_id}:${process.pid}:${process.start_time_utc ?? "unknown"}`;
}

function populateProcessSelect(processes) {
    const previousSelection = processSelect.value;

    processSelect.replaceChildren();

    for (const process of processes) {
        const option = document.createElement("option");

        // Store the process identity needed by the history API.
        option.value = JSON.stringify({
            process_instance_id:
                `${process.pid}_${process.start_time_utc ?? ""}`
        });

        option.textContent =
            `${process.process_name ?? "Unknown"} (PID ${process.pid})`;

        processSelect.appendChild(option);
    }

    // Preserve the user's selection across refreshes.
    const previousOptionExists = [...processSelect.options].some(
        option => option.value === previousSelection
    );

    if (previousOptionExists) {
        processSelect.value = previousSelection;
    }
}

function renderHistory(records) {
    const labels = records.map(record =>
        formatTime(record.timestamp_utc)
    );

    const readRates = records.map(record =>
        record.read_bytes_per_sec == null
            ? null
            : Number(record.read_bytes_per_sec) / 1_000_000
    );

    const writeRates = records.map(record =>
        record.write_bytes_per_sec == null
            ? null
            : Number(record.write_bytes_per_sec) / 1_000_000
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
                        tension: 0.2
                    },
                    {
                        label: "Write (MB/s)",
                        data: writeRates,
                        borderColor: "#D97706",
                        backgroundColor: "#D97706",
                        tension: 0.2
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

async function refreshHistory() {
    if (isRefreshing) return;

    isRefreshing = true;

    try {
        // Polling also accumulates samples when mock mode is enabled.
        const processes = await getLatestProcesses();

        if (!Array.isArray(processes)) {
            throw new Error("Expected an array of process records.");
        }

        populateProcessSelect(processes);

        if (!processSelect.value && processes.length > 0) {
            processSelect.selectedIndex = 0;
        }

        const selectedValue = processSelect.value;

        if (!selectedValue) {
            statusElement.textContent = "No processes available.";
            renderHistory([]);
            return;
        }

        const selectedProcess = JSON.parse(selectedValue);

        const end = new Date();
        const start = new Date(end.getTime() - HISTORY_WINDOW_MS);

        const records = await getProcessHistory({
            ...selectedProcess,
            start_utc: start.toISOString(),
            end_utc: end.toISOString()
        });

        renderHistory(records);

        statusElement.textContent =
            `${records.length} samples · Last 1 minute · Updated ${formatTime(end)}`;
    } catch (error) {
        console.error("Failed to load process history:", error);
        statusElement.textContent =
            "Unable to load process history. Retrying...";
    } finally {
        isRefreshing = false;
        setTimeout(refreshHistory, REFRESH_INTERVAL_MS);
    }
}

processSelect.addEventListener("change", () => {
    refreshHistory();
});

refreshHistory();
