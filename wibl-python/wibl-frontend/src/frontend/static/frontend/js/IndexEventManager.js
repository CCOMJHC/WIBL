

// Logic to manage filter drop down menu
document.addEventListener('DOMContentLoaded', () => {
    const filterSection = document.querySelector('#filterSection');
    const button = document.querySelector('#showButton');
    button.addEventListener('click', () => {
        if (filterSection.className === "box is-hidden") {
            filterSection.setAttribute("class", "box");
        } else {
            filterSection.setAttribute("class", "box is-hidden");
        }
    });
});

// Clear button in the filter menu
const clearButton = document.getElementById("clearButton");
clearButton.addEventListener("click", (event) => {
    let wiblFileTable = document.getElementById("wibl-file-table");
    wiblFileTable.clearCSS();
})

// Filter/search button in the filter menu
const filterButton = document.getElementById("filterButton");
filterButton.addEventListener("click", (event) => {
    var wiblFileTable = document.getElementById("wibl-file-table");
    var dateInput = document.getElementById("dateInput");
    var timeInput = document.getElementById("timeInput");
    var platformInput = document.getElementById("platformInput");
    var loggerInput = document.getElementById("loggerInput");
    wiblFileTable.filterTable(dateInput, timeInput, platformInput, loggerInput);
})

// Download button logic
// Can only download one file at a time currently
const downloadButton = document.getElementById("downloadButton");
downloadButton.addEventListener("click", (event) => {
    var wiblFileTable = document.getElementById("wibl-file-table");
    var result = wiblFileTable.getSelectedFiles(1);
    if (result != 0) {
        if (result.length > 1) {
            alert("Multiple files selected. Please select only one file to download.");
            return;
        } else {
            const url = `/downloadWiblFile/${result[0]}`;
            window.location.href = url;
        }
    }
})

