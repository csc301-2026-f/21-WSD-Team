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

button.addEventListener("click", function () {
    graph.classList.toggle("hidden");

    if (graph.classList.contains("hidden")) {
        button.textContent = "Show Graph";
    } else {
        button.textContent = "Hide Graph";
    }
});