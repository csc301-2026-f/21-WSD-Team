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
        value ?? "Not available"
    );

    row.append(heading, content);
    card.appendChild(row);
}

function formatDate(timestamp) {
    if (!timestamp) return "Not available";

    const date = new Date(timestamp);

    return Number.isNaN(date.getTime())
        ? "Not available"
        : date.toLocaleString();
}

function renderRecommendations(recommendations) {
    container.replaceChildren();

    if (!Array.isArray(recommendations)) {
        throw new Error("Expected a list of recommendations.");
    }
    
    // TEMPORARY: Display only the most recent recommendation.
    recommendations = [...recommendations].sort(
        (a, b) =>
            new Date(b.created_at_utc).getTime() -
            new Date(a.created_at_utc).getTime()
    ).slice(0, 1);

    if (recommendations.length === 0) {
        container.appendChild(
            createElement(
                "p",
                "recommendations-empty",
                "No saved recommendations. Select Refresh Recommendations to generate them."
            )
        );
        return;
    }

    for (const recommendation of recommendations) {
        const card = createElement("article", "recommendation-card");

        const header = createElement(
            "div",
            "recommendation-card-header"
        );

        const titleGroup = createElement("div", "recommendation-title-group");

        titleGroup.append(
            createElement(
                "h3",
                "",
                recommendation.file_id ?? "Storage recommendation"
            ),
            createElement(
                "p",
                "recommendation-subtitle",
                `${recommendation.mode ?? "Unknown mode"} · ${recommendation.action ?? "No action"}`
            )
        );

        const approvalBadge = createElement(
            "span",
            recommendation.requires_approval
                ? "recommendation-badge approval-required"
                : "recommendation-badge",
            recommendation.requires_approval
                ? "Approval required"
                : "Approval not flagged"
        );

        header.append(titleGroup, approvalBadge);
        card.appendChild(header);

        addDetail(card, "Reason", recommendation.reason);
        addDetail(card, "Source device", recommendation.source_device_id);
        addDetail(card, "Target device", recommendation.target_device_id);
        addDetail(
            card,
            "Estimated benefit",
            recommendation.estimated_benefit == null
                ? "Unavailable"
                : JSON.stringify(recommendation.estimated_benefit)
        );
        addDetail(
            card,
            "Generated",
            formatDate(recommendation.created_at_utc)
        );

        const constraints = Array.isArray(recommendation.constraints)
            ? recommendation.constraints
            : [];

        const constraintsHeading = createElement("h4", "", "Constraints");
        card.appendChild(constraintsHeading);

        if (constraints.length === 0) {
            card.appendChild(
                createElement("p", "", "No constraints provided.")
            );
        } else {
            const list = createElement("ul", "recommendation-constraints");

            for (const constraint of constraints) {
                list.appendChild(createElement("li", "", constraint));
            }

            card.appendChild(list);
        }

        card.appendChild(
            createElement(
                "p",
                "recommendation-id",
                `ID: ${recommendation.recommendation_id ?? "Unavailable"}`
            )
        );

        container.appendChild(card);
    }
}

async function loadRecommendations() {
    statusElement.textContent = "Loading saved recommendations...";

    try {
        const recommendations = await getRecommendations();
        renderRecommendations(recommendations);

        statusElement.textContent =
            `${recommendations.length} saved recommendation(s).`;
    } catch (error) {
        console.error("Failed to load recommendations:", error);

        statusElement.textContent =
            "Could not load recommendations. Check that Flask is running and browser access is allowed.";

        container.replaceChildren();
    }
}

async function handleRefresh() {
    if (isRefreshing) return;

    isRefreshing = true;
    refreshButton.disabled = true;
    refreshButton.textContent = "Refreshing...";
    statusElement.textContent = "Generating recommendations...";

    try {
        // POST runs the algorithm and returns the generated records.
        const generated = await refreshRecommendations();

        if (!Array.isArray(generated)) {
            throw new Error("Expected the refresh response data to be an array.");
        }

        // Display the actual response from POST.
        renderRecommendations(generated);

        statusElement.textContent =
            `${generated.length} recommendation(s) generated and returned.`;

        // GET verifies and displays what was saved.
        await loadRecommendations();
    } catch (error) {
        console.error("Failed to refresh recommendations:", error);

        statusElement.textContent =
            "Could not refresh recommendations. Check the backend and try again.";
    } finally {
        isRefreshing = false;
        refreshButton.disabled = false;
        refreshButton.textContent = "Refresh Recommendations";
    }
}

refreshButton.addEventListener("click", handleRefresh);

loadRecommendations();
