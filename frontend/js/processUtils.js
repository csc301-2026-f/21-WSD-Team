
/* PROCESS IDENTIFICATION */

export function getProcessKey(process) {
    return `${process.host_id}:${process.pid}:${process.start_time_utc ?? "unknown"}`;
}


/* PROCESS RATE FORMATTING */

export function formatRate(bytesPerSecond) {
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


/* PROCESS SEARCH AND FILTERING */

export function filterProcesses(processes, searchTerm = "") {
    if (!Array.isArray(processes)) {
        return [];
    }

    const query = String(searchTerm).trim().toLowerCase();

    if (query === "") {
        return [...processes];
    }

    return processes.filter(process => {
        const name = String(
            process.process_name ?? ""
        ).toLowerCase();

        const pid = String(
            process.pid ?? ""
        );

        return name.includes(query) || pid.includes(query);
    });
}
