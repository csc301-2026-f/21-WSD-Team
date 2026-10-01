/* Set the width of the sidebar to 250px and the left margin of the page content to 250px */
function openNav() {
  document.getElementById("mySidebar").style.width = "250px";
  document.getElementById("main").style.marginLeft = "250px";
}

/* Set the width of the sidebar to 0 and the left margin of the page content to 0 */
function closeNav() {
  document.getElementById("mySidebar").style.width = "0";
  document.getElementById("main").style.marginLeft = "0";
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