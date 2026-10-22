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
