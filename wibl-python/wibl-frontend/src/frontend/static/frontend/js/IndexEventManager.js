

//Drop down logic
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

const clearButton = document.getElementById("clearButton");
clearButton.addEventListener("click", (event) => {
    let wiblFileTable = document.getElementById("wibl-file-table");
    wiblFileTable.clearCSS();
})

const filterButton = document.getElementById("filterButton");
filterButton.addEventListener("click", (event) => {
    var wiblFileTable = document.getElementById("wibl-file-table");
    var dateInput = document.getElementById("dateInput");
    var timeInput = document.getElementById("timeInput");
    var platformInput = document.getElementById("platformInput");
    var loggerInput = document.getElementById("loggerInput");
    wiblFileTable.filterTable(dateInput, timeInput, platformInput, loggerInput);
})


const deleteButton = document.getElementById("deleteButton");
deleteButton.addEventListener("click", (event) => {
    var wiblFileTable = document.getElementById("wibl-file-table");
    var result = wiblFileTable.getSelectedFiles(0);
    if (result != 0) {
        const wiblSockType = "wibl";
        const wiblSockUrl = "{{ wsURL }}" + wiblSockType + "/table";
        const wiblSock = SocketManager.getInstance(wiblSockUrl, wiblSockType);
        wiblSock.sendRequest("delete-wibl-files", {"file_ids" : result});
        wiblSock.sendRequest("list-wibl-files");
    }
})

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

const testDownloadButton = document.getElementById("testDownloadButton")
testDownloadButton.addEventListener("click", (event) => {
    const url = `/downloadWiblFile/test_file.txt`;
    window.location.href = url;
})