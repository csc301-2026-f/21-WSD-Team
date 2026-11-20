// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { getCapabilities } from "./api.js";

const body = document.getElementById("capabilities-body");
const status = document.getElementById("configuration-status");
const features = [
    ["Device metrics", "device_metrics"],
    ["Process metrics", "process_metrics"],
    ["Process to device attribution", "process_to_device_attribution"],
    ["File access metrics", "file_access_metrics"],
    ["File level pooling (RAID 0 mode)", "file_level_pooling"],
    ["SSD caching", "ssd_caching"],
    ["File move execution", "file_move"],
    ["Dry run action", "dry_run_action"]
];

function render(capabilities) {
    body.replaceChildren();
    for (const [label, key] of features) {
        const row = document.createElement("tr");
        const name = document.createElement("td"); name.textContent = label;
        const state = document.createElement("td");
        const value = capabilities && Object.hasOwn(capabilities, key) ? capabilities[key] : null;
        state.textContent = value === true ? "Supported" : value === false ? "Unavailable" : "Not reported";
        const details = document.createElement("td");
        details.textContent = value === true ? "Reported by the backend; no configuration control is exposed here." : "No active frontend control or supporting configuration endpoint.";
        row.append(name, state, details); body.appendChild(row);
    }
}

getCapabilities().then(capabilities => {
    render(capabilities);
    status.textContent = "Capabilities loaded from the connected backend.";
}).catch(error => {
    render(null);
    status.textContent = `Could not load backend capabilities: ${error.message}`;
});
