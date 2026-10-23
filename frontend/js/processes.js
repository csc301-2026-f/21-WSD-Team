// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { getLatestProcesses } from "./api.js";

const REFRESH_INTERVAL_MS = 2000;

const tableBody = document.getElementById("process-table-body");
const statusElement = document.getElementById("process-status");
const selectedElement = document.getElementById("selected-process");

let selectedProcessKey = null;
let isRefreshing = false;

function getProcessKey(process) {
    return `${process.host_id}:${process.pid}:${process.start_time_utc ?? "unknown"}`;
}

function formatRate(bytesPerSecond) {
    if (bytesPerSecond == null) {
        return "N/A";
    }
    const value = Number(bytesPerSecond);
    

    if (!Number.isFinite(value) || value < 0) {
        return "N/A";
    }

    if (value >= 1_000_000) {
        return `${(value / 1_000_000).toFixed(2)} MB/s`;
    }

    if (value >= 1_000) {
        return `${(value / 1_000).toFixed(2)} KB/s`;
    }

    return `${value.toFixed(0)} B/s`;
}

function renderProcesses(processes) {
    tableBody.replaceChildren();

    for (const process of processes) {
        const processKey = getProcessKey(process);
        const row = document.createElement("tr");

        row.dataset.processKey = processKey;

        const values = [
            process.process_name ?? "Unknown",
            process.pid ?? "N/A",
            formatRate(process.read_bytes_per_sec),
            formatRate(process.write_bytes_per_sec),
            process.attributed_device_id ?? "Unattributed"
        ];

        for (const value of values) {
            const cell = document.createElement("td");
            cell.textContent = String(value);
            row.appendChild(cell);
        }

        if (processKey === selectedProcessKey) {
            row.classList.add("selected-process-row");
        }

        row.addEventListener("click", () => {
            selectedProcessKey = processKey;

            selectedElement.textContent =
                `Selected: ${process.process_name ?? "Unknown"} ` +
                `(PID ${process.pid}, host ${process.host_id})`;

            for (const existingRow of tableBody.rows) {
                existingRow.classList.toggle(
                    "selected-process-row",
                    existingRow.dataset.processKey === selectedProcessKey
                );
            }
        });

        tableBody.appendChild(row);
    }
}

async function refreshProcessTable() {
    if (isRefreshing) return;

    isRefreshing = true;

    try {
        const processes = await getLatestProcesses();

        if (!Array.isArray(processes)) {
            throw new Error("Expected an array of process records.");
        }

        renderProcesses(processes);

        statusElement.textContent =
            `${processes.length} processes · Last updated ` +
            new Date().toLocaleTimeString();
    } catch (error) {
        console.error("Failed to load process data:", error);
        statusElement.textContent =
            "Unable to load process data. Retrying...";
    } finally {
        isRefreshing = false;
        setTimeout(refreshProcessTable, REFRESH_INTERVAL_MS);
    }
}

refreshProcessTable();
