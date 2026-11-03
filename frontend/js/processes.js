
import { getLatestProcesses } from "./api.js";

const REFRESH_INTERVAL_MS = 2000;

const tableBody = document.getElementById("process-table-body");
const statusElement = document.getElementById("process-status");
const selectedElement = document.getElementById("selected-process");
const searchInput = document.getElementById("process-search");

let selectedProcessKey = null;
let latestProcesses = [];
let isRefreshing = false;

/* PROCESS IDENTIFICATION */

function getProcessKey(process) {
    return `${process.host_id}:${process.pid}:${process.start_time_utc ?? "unknown"}`;
}

/* FORMATTING */

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

/* RENDER PROCESS TABLE */

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
            cell.textContent = value;
            row.appendChild(cell);
        }

        if (processKey === selectedProcessKey) {
            row.classList.add("selected-process");
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

            // Tell the history graph which process was selected.
            document.dispatchEvent(
                new CustomEvent("process-selected-for-history", {
                    detail: {
                        process_instance_id:
                            `${process.pid}_${process.start_time_utc ?? ""}`
                    }
                })
            );
        });

        tableBody.appendChild(row);
    }

    if (processes.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.textContent = latestProcesses.length === 0
            ? "No processes available."
            : "No processes match your search.";

        row.appendChild(cell);
        tableBody.appendChild(row);
    }
}

/* SEARCH AND FILTERING */

function getFilteredProcesses() {
    const searchTerm = searchInput.value.trim().toLowerCase();

    return latestProcesses.filter(process => {
        const name = String(
            process.process_name ?? ""
        ).toLowerCase();

        const pid = String(
            process.pid ?? ""
        );

        return name.includes(searchTerm) || pid.includes(searchTerm);
    });
}

function filterProcesses() {
    const filteredProcesses = getFilteredProcesses();

    renderProcesses(filteredProcesses);

    if (searchInput.value.trim() !== "") {
        statusElement.textContent =
            `Showing ${filteredProcesses.length} of ${latestProcesses.length} processes.`;
    }
}

/* REFRESH PROCESS DATA */

async function refreshProcessTable() {
    if (isRefreshing) {
        return;
    }

    isRefreshing = true;

    try {
        const processes = await getLatestProcesses();

        if (!Array.isArray(processes)) {
            throw new Error("Expected an array of process records.");
        }

        latestProcesses = processes;

        // Preserve the search when new data arrives.
        filterProcesses();

        // Clear selection if the selected process no longer exists.
        if (
            selectedProcessKey !== null &&
            !latestProcesses.some(
                process => getProcessKey(process) === selectedProcessKey
            )
        ) {
            selectedProcessKey = null;
            selectedElement.textContent = "No process selected.";
        }

        if (searchInput.value.trim() === "") {
            statusElement.textContent =
                `${latestProcesses.length} processes detected.`;
        }

    } catch (error) {
        console.error("Failed to refresh process table:", error);

        statusElement.textContent =
            "Unable to load processes. Retrying...";

    } finally {
        isRefreshing = false;
        setTimeout(refreshProcessTable, REFRESH_INTERVAL_MS);
    }
}

/* EVENT LISTENERS */

searchInput.addEventListener("input", filterProcesses);

/* INITIALIZATION */

refreshProcessTable();
