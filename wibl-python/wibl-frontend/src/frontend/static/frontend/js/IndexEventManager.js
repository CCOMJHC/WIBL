

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
    var geojsonFileTable = document.getElementById("geojson-file-table");

    var wiblResult = wiblFileTable.getSelectedFiles(1);
    var geojsonResult = geojsonFileTable.getSelectedFiles(1);

    var result = wiblResult.concat(geojsonResult);

    if (result.length != 0) {
        if (result.length > 1) {
            alert("Multiple files selected. Please select only one file to download.");
            return;
        } else {
            const url = `/downloadFile/${result[0]}`;
            fetch(url, {
                method: 'GET'
            }).then(async response => {
                const contentType = response.headers.get("content-type") || "";
                if (!response.ok) {
                    if (contentType.includes("application/json")) {
                        const errorData = await response.json();
                        alert(JSON.stringify(errorData, null, 2));
                    } else {
                        alert(`Unexpected error: ${response.status}`);
                    }
                } else {
                    const disposition = response.headers.get("Content-Disposition") || "";
                    const filenameMatch = disposition.match(/filename\s*=\s*(?:"([^"]+)"|([^;\n]+))/);
                    const filename = filenameMatch[1];

                    const blob = await response.blob();

                    const blobUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = blobUrl;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(blobUrl);
                }
            }).catch(err => {
                alert(`Network error: ${err}`);
            });
        }
    } else {
        alert("No Files Selected.")
    }
})