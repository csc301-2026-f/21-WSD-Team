import { formatRate } from "./processUtils.js";

// Convert a process record into the values displayed in its table row.
export function getProcessRowValues(process) {
    return [
        process.process_name ?? "Unknown",
        process.pid ?? "N/A",
        formatRate(process.read_bytes_per_sec),
        formatRate(process.write_bytes_per_sec),
        process.attributed_device_id ?? "Unattributed"
    ];
}

// Determine which message to display when the process table is empty.
export function getEmptyStateMessage(latestProcesses) {
    return latestProcesses.length === 0
        ? "No processes available."
        : "No processes match your search.";
}

// Determine the status message displayed above the process table.
export function getProcessStatusMessage(latestProcesses, searchTerm = "") {
    const query = String(searchTerm).trim();

    if (query !== "") {
        const filteredProcesses = latestProcesses.filter(process => {
            const name = String(process.process_name ?? "").toLowerCase();
            const pid = String(process.pid ?? "");
            const normalizedQuery = query.toLowerCase();

            return name.includes(normalizedQuery) ||
                pid.includes(normalizedQuery);
        });

        return `Showing ${filteredProcesses.length} of ${latestProcesses.length} processes.`;
    }

    return `${latestProcesses.length} processes detected.`;
}