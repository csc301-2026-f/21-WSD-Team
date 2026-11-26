// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
import { getCapabilities } from "./api.js";

const body = document.getElementById("capabilities-body");
const status = document.getElementById("configuration-status");
const modeRadios = [...document.querySelectorAll('input[name="storage-mode"]')];
const modeSelectionNote = document.getElementById("mode-selection-note");
const modeToast = document.getElementById("mode-selection-toast");
const modeToastMessage = document.getElementById("mode-selection-toast-message");
let toastDismissTimer = null;
let toastHideTimer = null;
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

function updateSelection() {
    const selected = modeRadios.find(radio => radio.checked)?.value;
    const label = selected === "ssd_caching" ? "SSD Caching" : "RAID 0 / File-Level Pooling";
    modeSelectionNote.textContent = `${label} selected for this page preview. This does not change system configuration.`;
}

function showModeSelectionToast(selected) {
    if (!modeToast || !modeToastMessage) return;

    window.clearTimeout(toastDismissTimer);
    window.clearTimeout(toastHideTimer);
    modeToast.classList.remove("is-leaving", "is-entering");

    const label = selected === "ssd_caching" ? "SSD Caching" : "RAID 0";
    modeToastMessage.textContent = `${label} selected (Preview)`;
    modeToast.hidden = false;
    void modeToast.offsetWidth;
    modeToast.classList.add("is-entering");

    toastDismissTimer = window.setTimeout(() => {
        modeToast.classList.remove("is-entering");
        modeToast.classList.add("is-leaving");
        toastHideTimer = window.setTimeout(() => {
            modeToast.hidden = true;
            modeToast.classList.remove("is-leaving");
        }, 240);
    }, 2760);
}

function renderModeStatus(capabilities, key, badgeId, detailId, implementationDetail) {
    const badge = document.getElementById(badgeId);
    const detail = document.getElementById(detailId);
    const value = capabilities && Object.hasOwn(capabilities, key) ? capabilities[key] : null;
    if (value === true) {
        badge.textContent = "Reported available";
        badge.dataset.state = "available";
        detail.textContent = `Backend reports support. ${implementationDetail}`;
    } else if (value === false) {
        badge.textContent = "Unavailable";
        badge.dataset.state = "unavailable";
        detail.textContent = `Backend reports this feature is unavailable. ${implementationDetail}`;
    } else {
        badge.textContent = "Not reported";
        badge.dataset.state = "unknown";
        detail.textContent = `The backend did not report this capability. ${implementationDetail}`;
    }
}

function render(capabilities) {
    renderModeStatus(capabilities, "file_level_pooling", "raid0-status-badge", "raid0-status-detail",
        "WSD does not expose mergerfs mount configuration or a mode-switch API.");
    renderModeStatus(capabilities, "ssd_caching", "cache-status-badge", "cache-status-detail",
        "Cache routing and execution are not exposed through the current API.");
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

modeRadios.forEach(radio => radio.addEventListener("change", () => {
    updateSelection();
    showModeSelectionToast(radio.value);
}));
updateSelection();

getCapabilities().then(capabilities => {
    render(capabilities);
    status.textContent = "Capabilities loaded from the connected backend.";
}).catch(error => {
    render(null);
    status.textContent = `Could not load backend capabilities: ${error.message}. Mode availability is unknown.`;
});
