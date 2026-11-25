// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only

const links = [
    ["Overview", "overview.html", "Overview"],
    ["Live Dashboard", "index.html", "Monitoring"],
    ["Disk Usage Statistics", "stats.html", "Monitoring"],
    ["Storage Analytics", "analytics.html", "Monitoring"],
    ["Process Analytics", "process_analytics.html", "Monitoring"],
    ["File I/O Monitoring", "file_io.html", "Monitoring"],
    ["Drive Management", "drives.html", "Storage"],
    ["Storage Configuration", "settings.html", "Storage"],
    ["Recommendations", "recommendations.html", "Optimization"],
    ["Data Export", "export.html", "Reports"],
    ["About", "about.html", "Information"],
    ["Group Info", "authors.html", "Information"]
];

const sidenav = document.getElementById("mainSidenav");
const openButton = document.getElementById("navOpenButton");

function closeNav() {
    sidenav.style.width = "0";
    openButton.setAttribute("aria-expanded", "false");
}

function openNav() {
    sidenav.style.width = "min(280px, 88vw)";
    openButton.setAttribute("aria-expanded", "true");
    sidenav.querySelector(".closebtn").focus();
}

if (sidenav && openButton) {
    sidenav.replaceChildren();
    const close = document.createElement("button");
    close.type = "button";
    close.id = "navCloseButton";
    close.className = "closebtn";
    close.textContent = "×";
    close.setAttribute("aria-label", "Close navigation");
    close.addEventListener("click", closeNav);
    sidenav.appendChild(close);

    const path = location.pathname.split("/").pop() || "index.html";
    let section = "";
    for (const [label, href, group] of links) {
        if (group !== section) {
            section = group;
            const heading = document.createElement("h2");
            heading.className = "sidenav-section";
            heading.textContent = group;
            sidenav.appendChild(heading);
        }
        const link = document.createElement("a");
        link.href = href;
        link.textContent = label;
        if (href === path) {
            link.classList.add("active");
            link.setAttribute("aria-current", "page");
        }
        sidenav.appendChild(link);
    }

    openButton.setAttribute("role", "button");
    openButton.setAttribute("tabindex", "0");
    openButton.setAttribute("aria-label", "Open navigation");
    openButton.setAttribute("aria-controls", "mainSidenav");
    openButton.setAttribute("aria-expanded", "false");
    openButton.addEventListener("click", openNav);
    openButton.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openNav();
        }
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape") closeNav();
    });
}
