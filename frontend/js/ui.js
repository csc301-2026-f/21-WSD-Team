// SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
// SPDX-License-Identifier: GPL-3.0-only
function openNav() {
  document.getElementById("mainSidenav").style.width = "250px";
  document.getElementById("navOpenButton").style.opacity = "0%";
}

function closeNav() {
  document.getElementById("mainSidenav").style.width = "0";
  document.getElementById("navOpenButton").style.opacity = "80%";
}

const button = document.getElementById("show-button");
const graph = document.getElementById("graph");

document.getElementById("navOpenButton")
    .addEventListener("click", openNav);

document.getElementById("navCloseButton")
    .addEventListener("click", closeNav);

console.log("UI Module Loaded")
