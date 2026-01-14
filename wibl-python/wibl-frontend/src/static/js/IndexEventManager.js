

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
    wiblFileTable.clearAll();
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
downloadButton.addEventListener("click", async (event) => {

    var wiblFileTable = document.getElementById("wibl-file-table");
    var geojsonFileTable = document.getElementById("geojson-file-table");

    var wiblResult = wiblFileTable.getSelectedFiles(1);
    var geojsonResult = geojsonFileTable.getSelectedFiles(1);

    var result = wiblResult.concat(geojsonResult);

    if (result != 0) {
        if (result.length > 1) {
            alert("Multiple files selected. Please select only one file to download.");
            return;
        } else {
            const check_url = `/check/${result[0]}`;
            const response = await fetch(check_url);
            const status = response.status
            if (status == 200) {
                const url = `/downloadFile/${result[0]}`;
                window.location.href = url;
            } else {
                alert(`File ${result[0]} could not be found.`)
            }
        }
    } else {
        alert("No Files Selected.")
    }
})

