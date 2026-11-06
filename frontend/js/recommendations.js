// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only

import {
    getRecommendations,
    refreshRecommendations
} from "./api.js";

const container = document.getElementById("recommendations-container");
const statusElement = document.getElementById("recommendations-status");
const refreshButton = document.getElementById(
    "refresh-recommendations-button"
);

let isRefreshing = false;

/* ELEMENT CREATION */

function createElement(tag, className, text) {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined && text !== null) {
        element.textContent = String(text);
    }

    return element;
}

function addDetail(card, label, value) {
    const row = createElement("p", "recommendation-detail");
    const heading = createElement("strong", "", `${label}: `);
    const content = createElement(
        "span",
        "",
        formatValue(value)
    );

    row.append(heading, content);
    card.appendChild(row);
}

/* DATA FORMATTING */

function formatValue(value) {
    if (value === null || value === undefined || value === "") {
        return "Not available";
    }

    if (Array.isArray(value)) {
        return value.length > 0
            ? value.map(formatValue).join(", ")
            : "None";
    }

    if (typeof value === "object") {
        return Object.entries(value)
            .map(([key, item]) => `${key}: ${formatValue(item)}`)
            .join(" | ");
    }

    return String(value);
}

function formatDate(timestamp) {
    if (!timestamp) return "Not available";

    const date = new Date(timestamp);

    return Number.isNaN(date.getTime())
        ? "Not available"
        : date.toLocaleString();
}

function sortRecommendations(recommendations) {
    return [...recommendations].sort((a, b) => {
        const dateA = Date.parse(a.created_at_utc);
        const dateB = Date.parse(b.created_at_utc);

        const validA = Number.isFinite(dateA);
        const validB = Number.isFinite(dateB);

        if (!validA && !validB) return 0;
        if (!validA) return 1;
        if (!validB) return -1;

        return dateB - dateA;
    });
}

/* EMPTY AND ERROR STATES */

function showMessage(
    message,
    className = "recommendations-empty"
) {
    container.replaceChildren(
        createElement("p", className, message)
    );
}

/* RECOMMENDATION RENDERING */

function renderRecommendations(recommendations) {
    if (!Array.isArray(recommendations)) {
        throw new Error("Expected a list of recommendations.");
    }

    const validRecommendations = recommendations.filter(
        recommendation =>
            recommendation !== null &&
            typeof recommendation === "object" &&
            !Array.isArray(recommendation)
    );

    const sortedRecommendations =
        sortRecommendations(validRecommendations);

    container.replaceChildren();

    if (sortedRecommendations.length === 0) {
        showMessage(
            "No recommendations are currently available."
        );

        return 0;
    }

    for (const recommendation of sortedRecommendations) {
        const card = createElement(
            "article",
            "recommendation-card"
        );

        /* HEADER */

        const header = createElement(
            "div",
            "recommendation-card-header"
        );

        const titleGroup = createElement(
            "div",
            "recommendation-title-group"
        );

        const hasFile = recommendation.file_id !== null &&
            recommendation.file_id !== undefined &&
            recommendation.file_id !== "";

        const title = hasFile
            ? `File ID: ${recommendation.file_id}`
            : "Storage recommendation";

        const mode = recommendation.mode ?? "Unknown mode";
        const action = recommendation.action ?? "Unknown action";

        titleGroup.append(
            createElement("h3", "", title),
            createElement(
                "p",
                "recommendation-subtitle",
                `${mode} · ${action}`
            )
        );

        const approvalRequired =
            recommendation.requires_approval === true;

        const approvalBadge = createElement(
            "span",
            approvalRequired
                ? "recommendation-badge approval-required"
                : "recommendation-badge",
            approvalRequired
                ? "Approval required"
                : "No approval flagged"
        );

        header.append(titleGroup, approvalBadge);
        card.appendChild(header);

        /* DETAILS */

        addDetail(card, "Reason", recommendation.reason);
        addDetail(card, "Source device", recommendation.source_device_id);
        addDetail(card, "Target device", recommendation.target_device_id);
        addDetail(card, "Estimated benefit", recommendation.estimated_benefit);
        addDetail(card, "Generated", formatDate(recommendation.created_at_utc));

        /* CONSTRAINTS */

        const constraints = Array.isArray(recommendation.constraints)
            ? recommendation.constraints
            : [];

        card.appendChild(
            createElement("h4", "", "Constraints")
        );

        if (constraints.length === 0) {
            card.appendChild(
                createElement("p", "", "No constraints provided.")
            );
        } else {
            const list = createElement(
                "ul",
                "recommendation-constraints"
            );

            for (const constraint of constraints) {
                list.appendChild(
                    createElement("li", "", formatValue(constraint))
                );
            }

            card.appendChild(list);
        }

        /* IDENTIFIER */

        card.appendChild(
            createElement(
                "p",
                "recommendation-id",
                `ID: ${recommendation.recommendation_id ?? "Unavailable"}`
            )
        );

        container.appendChild(card);
    }

    return sortedRecommendations.length;
}

/* LOAD SAVED RECOMMENDATIONS */

async function loadRecommendations() {
    statusElement.textContent =
        "Loading saved recommendations...";

    try {
        const recommendations = await getRecommendations();

        const displayedCount =
            renderRecommendations(recommendations);

        statusElement.textContent =
            `${displayedCount} saved recommendation(s).`;

    } catch (error) {
        console.error("Failed to load recommendations:", error);

        statusElement.textContent =
            "Could not load recommendations. Check that Flask is running.";

        showMessage(
            "Unable to load recommendations. Please try again.",
            "recommendations-error"
        );
    }
}

/* REFRESH RECOMMENDATIONS */

async function handleRefresh() {
    if (isRefreshing) return;

    isRefreshing = true;

    refreshButton.disabled = true;
    refreshButton.textContent = "Refreshing...";
    statusElement.textContent = "Generating recommendations...";

    try {
        // The backend generates and saves recommendations before returning.
        const generated = await refreshRecommendations();

        if (!Array.isArray(generated)) {
            throw new Error(
                "Expected the refresh response data to be an array."
            );
        }

        const generatedCount =
            renderRecommendations(generated);

        statusElement.textContent =
            `${generatedCount} new recommendation(s) generated and saved.`;

    } catch (error) {
        console.error("Failed to refresh recommendations:", error);

        statusElement.textContent =
            "Could not generate recommendations. Check the backend and try again.";

        // Do not erase previously displayed recommendations on failure.
        if (container.childElementCount === 0) {
            showMessage(
                "Recommendation generation failed. Please try again.",
                "recommendations-error"
            );
        }

    } finally {
        isRefreshing = false;
        refreshButton.disabled = false;
        refreshButton.textContent = "Refresh Recommendations";
    }
}

/* INITIALIZATION */

if (!container || !statusElement || !refreshButton) {
    console.error(
        "Recommendations page is missing one or more required HTML elements."
    );
} else {
    refreshButton.addEventListener("click", handleRefresh);
    loadRecommendations();
}
