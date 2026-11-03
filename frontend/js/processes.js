
import { getLatestProcesses } from "./api.js";

import {
    getProcessKey,
    formatRate,
    filterProcesses as filterProcessList
} from "./processUtils.js";

const REFRESH_INTERVAL_MS = 2000;

const tableBody = document.getElementById("process-table-body");
const statusElement = document.getElementById("process-status");
const selectedElement = document.getElementById("selected-process");
const searchInput = document.getElementById("process-search");

let selectedProcessKey = null;
let latestProcesses = [];
let isRefreshing = false;


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

function filterAndRenderProcesses() {
    const searchTerm = searchInput.value;

    const filteredProcesses = filterProcessList(
        latestProcesses,
        searchTerm
    );

    renderProcesses(filteredProcesses);

    statusElement.textContent = searchTerm.trim() !== ""
        ? `Showing ${filteredProcesses.length} of ${latestProcesses.length} processes.`
        : `${latestProcesses.length} processes detected.`;
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

        // Preserve the search when new data arrives.
        filterAndRenderProcesses();

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

searchInput.addEventListener("input", filterAndRenderProcesses);


/* INITIALIZATION */

refreshProcessTable();
