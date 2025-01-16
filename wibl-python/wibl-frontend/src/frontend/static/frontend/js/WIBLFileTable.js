
// TODO: Add remaining headers...
const HEADERS = ["File ID", "Processed time", ""]

const input_headers = ["fileid", "processtime"]

class WIBLFileTable extends HTMLElement {
    constructor() {
        super();
        this._url = null;
        this._styleUrl = null;
        this._shadow = null;
        this._rawData = [];
    }

    static observedAttributes = ["url", "stylesheet"];

    connectedCallback() {
        console.log("wibl-file-table: Added to page.");
        const wsType = "wibl";
        const wsURL = this._url + wsType + "/table";
        const sock = SocketManager.getInstance(wsURL, wsType);

        // Create shadow DOM root
        const shadow = this.attachShadow({mode: "open"});
        let active = 0;
        this._shadow = shadow;

        // Apply external styles to the shadow dom
        const linkElem = document.createElement("link");
        linkElem.setAttribute("rel", "stylesheet");
        linkElem.setAttribute("href", this._styleUrl);
        shadow.appendChild(linkElem);


        // Create table
        const table = document.createElement("table");
        table.setAttribute("id", "wc-wibl-file-table");
        table.className = "table";
        shadow.appendChild(table);

        let raw = this._rawData;

        function WIBLFileTableHanlderListWiblFiles(message) {
            // TODO: Delete existing content in table to support re-loading of data.
            console.log("In WIBLFileTableHanlderListWiblFiles...");
            const table = shadow.getElementById("wc-wibl-file-table");
            if (active == 1) {
                let rows = table.children[1].rows;
                let i = 0;
                raw = [];
                Array.from(rows).forEach(row => row.remove());
                for (const wiblFile of message.message.files) {
                    let data = [];
                    const row = document.createElement("tr");

                    // fileid field
                    const fileName = wiblFile.fileid;
                    data[0] = fileName;
                    console.log(`Filename: ${fileName}`);
                    var td = document.createElement("td");
                    td.setAttribute("id", `wc-wibl-file-${fileName}`);
                    td.textContent = fileName;
                    row.appendChild(td);

                    // processtime field
                    td = document.createElement("td");
                    data[1] = wiblFile.processtime;
                    td.textContent = wiblFile.processtime;
                    row.appendChild(td);

                    // Add aditional search fields if needed
                    data[2] = wiblFile.platform;
                    data[3] = wiblFile.logger;
                    data[4] = wiblFile.starttime;
                    data[5] = wiblFile.endtime;

                    var td2 = document.createElement("td");
                    const checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.className = "row-checkbox";
                    td2.appendChild(checkbox);
                    row.appendChild(td2);
                    row.setAttribute("id", fileName);
                    table.children[1].appendChild(row);

                    raw[i] = data;
                    i++;
                }
            } else {
                // Create header
                const thead = document.createElement("thead");
                const headerRow = document.createElement("tr");
                // TODO: Programmatically loop over all headers and add them as elements to the row...
                for (const headerText of HEADERS) {
                    const header = document.createElement("th");
                    header.textContent = headerText;
                    headerRow.appendChild(header);
                }
                headerRow.setAttribute("class", "headerRow");
                thead.appendChild(headerRow)
                table.appendChild(thead);
                // Load WIBL file fields into table
                const tbody = document.createElement("tbody");
                let i = 0
                for (const wiblFile of message.message.files) {
                    let data = [];
                    const row = document.createElement("tr");

                    // fileid field
                    const fileName = wiblFile.fileid;
                    data[0] = fileName;
                    console.log(`Filename: ${fileName}`);
                    var td = document.createElement("td");
                    td.setAttribute("id", `wc-wibl-file-${fileName}`);
                    td.textContent = fileName;
                    row.appendChild(td);

                    // processtime field
                    td = document.createElement("td");
                    data[1] = wiblFile.processtime;
                    td.textContent = wiblFile.processtime;
                    row.appendChild(td);

                    // Add aditional search fields if needed
                    data[2] = wiblFile.platform;
                    data[3] = wiblFile.logger;
                    data[4] = wiblFile.starttime;
                    data[5] = wiblFile.endtime;

                    var td2 = document.createElement("td");
                    const checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.className = "row-checkbox";
                    td2.appendChild(checkbox);
                    row.appendChild(td2);
                    // TODO: Add remaining fields later...
                    row.setAttribute("id", fileName);
                    tbody.appendChild(row);

                    raw[i] = data;
                    i++;
                }
                table.appendChild(tbody);
            }
            active = 1;
        }

        function WIBLFileTableHanlderDeleteWiblFiles(message) {
            console.log(`Successfully Deleted Files \n${message['message'].join('\n')}`);
        }


        sock.addHandler("delete-wibl-files", WIBLFileTableHanlderDeleteWiblFiles);
        sock.addHandler("list-wibl-files", WIBLFileTableHanlderListWiblFiles);
    }

    disconnectedCallback() {
        console.log("wibl-file-table: Removed from page.");
    }

    adoptedCallback() {
        console.log("wibl-file-table: Moved to new page.");
    }

    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`wibl-file-table: Attribute ${name} has changed from ${oldValue} to ${newValue}.`);
        switch (name) {
            case "url":
                // URL should only be set on initialization since there is currently
                // not logic for
                this._url = newValue;
                break;
            case "stylesheet":
                this._styleUrl = newValue;
                break;
            default:
                console.warn(`Unknown attribute ${name}`);
        }
    }

    clearCSS() {
        const table_rows = this._shadow.querySelectorAll("tr");

        const hiddenMessage = document.querySelector("#emptyMessage");
        hiddenMessage.setAttribute("class", "is-hidden");

        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            row.setAttribute("class", "");
        }
    }

    // This function works by finding all elements that should be HIDDEN, as in not a part of the table after the filter.
    filterTable(date, time, platform, logger) {

        // Reset previous filter
        this.clearCSS();

        date = date.value;
        time = time.value;
        platform = platform.value;
        logger = logger.value;

        let dateInclude = true;
        let platformInclude = true;
        let loggerInclude = true;

        let hideCount = 0;

        let dateObj;

        if (date === "") {
            dateInclude = false;
        } else {
            const dateStr = `${date}T${time}`
            dateObj = new Date(dateStr);
        }

        if (platform === "") {
            platformInclude = false;
        }

        if (logger === "") {
            loggerInclude = false;
        }

        let files = [];
        var rows = this._rawData;

        // Filter
        for (let i = 0; i < rows.length; i++) {
            let dateMatch = false;
            let platformMatch = false;
            let loggerMatch = false;

            if (dateInclude) {
                let starttime = rows[i][4];
                let endtime = rows[i][5];

                starttime = starttime.slice(0, 16);
                endtime = endtime.slice(0, 16);
                const startObj = new Date(starttime);
                const endObj = new Date(endtime);

                if ((startObj < dateObj) && (dateObj < endObj)) {
                    dateMatch = true;
                }
            } else {
                dateMatch = true;
            }

            if (platformInclude) {
                let originPlatform = rows[i][2];
                if (originPlatform === platform) {
                    platformMatch = true;
                }
            } else {
                platformMatch = true;
            }

            if (loggerInclude) {
                let originLogger = rows[i][3];
                if (originLogger === logger) {
                    loggerMatch = true;
                }
            } else {
                loggerMatch = true;
            }

            if (!loggerMatch || !platformMatch || !dateMatch) {
                hideCount++;
                files.push(rows[i][0]);
            }
        }

        const table_rows = this._shadow.querySelectorAll("tr");

        // Apply CSS
        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            files.forEach((file) => {
                if (row.id === file) {
                    row.setAttribute("class", "is-hidden");
                }
            })
        }
        if (hideCount == rows.length) {
            let emptyMessage = document.querySelector("#emptyMessage");
            emptyMessage.setAttribute("class", "");
        }
    }

    getSelectedFiles(option) {
        const checkedBoxes = this._shadow.querySelectorAll('.row-checkbox:checked');

        const selectedNames = [];
        const selectedRows = [];

        checkedBoxes.forEach(checkbox => {
                const row = checkbox.closest('tr');
                selectedRows.push(row);
        });

        selectedRows.forEach(row => {
            const fileNameCell = row.querySelector('td:nth-of-type(1)');
            const fileName = fileNameCell.textContent;
            selectedNames.push(fileName);
        })

        if (selectedNames.length != 0) {

            //Delete files option = 0, download files option = 1

            let promptText;
            if (option == 0) {
                promptText = `Would you like to delete files: \n${selectedNames.join('\n')}?`;
            } else if (option == 1){
                promptText = `Would you like to download files: \n${selectedNames.join('\n')}?`;
            } else {
                return 0;
            }

            if (confirm(promptText)) {
                //uncheck all boxes
                checkedBoxes.forEach(checkbox => {
                    checkbox.checked = false;
                })

                return selectedNames;
            } else {
                console.log("Delete canceled");
                return 0;
            }
        } else {
            alert("No Files Selected To Delete.");
            return 0;
        }
    }

//    deleteSelectedFiles() {
//        console.log("deleteSelectedFiles() called...");
//
//        const checkedBoxes = this._shadow.querySelectorAll('.row-checkbox:checked');
//
//        const selectedNames = [];
//        const selectedRows = [];
//
//        checkedBoxes.forEach(checkbox => {
//                const row = checkbox.closest('tr');
//                selectedRows.push(row);
//        });
//
//        selectedRows.forEach(row => {
//            const fileNameCell = row.querySelector('td:nth-of-type(1)');
//            const fileName = fileNameCell.textContent;
//            selectedNames.push(fileName);
//        })
//
//        if (selectedNames.length != 0) {
//            const promptText = `Would you like to delete files: \n${selectedNames.join('\n')}?`;
//            if (confirm(promptText)) {
//                //TODO: Communicate with manager to delete files selected
//
//                //uncheck all boxes
//                checkedBoxes.forEach(checkbox => {
//                    checkbox.checked = false;
//                })
//
//                //TODO: Write a function that refreshes the file-table, put it here
//                return selectedNames;
//            } else {
//                console.log("Delete canceled");
//                return 0;
//            }
//        } else {
//            alert("No Files Selected To Delete.");
//            return 0;
//        }
//    }
//
//    downloadSelectedFiles() {
//        console.log("downloadSelectedFiles() called...");
//
//        const checkedBoxes = this._shadow.querySelectorAll('.row-checkbox:checked');
//
//        const selectedNames = [];
//        const selectedRows = [];
//
//        checkedBoxes.forEach(checkbox => {
//                const row = checkbox.closest('tr');
//                selectedRows.push(row);
//        });
//
//        selectedRows.forEach(row => {
//            const fileNameCell = row.querySelector('td:nth-of-type(1)');
//            const fileName = fileNameCell.textContent;
//            selectedNames.push(fileName);
//        })
//
//        if (selectedNames.length != 0) {
//            const promptText = `Would you like to archive files: ${selectedNames.join('\n')}?`;
//            if (confirm(promptText)) {
//                //TODO: Communicate with manager to archive files selected
//                console.log(`Selected Files: ${selectedNames.join(', ')}`);
//
//                //uncheck all boxes
//                checkedBoxes.forEach(checkbox => {
//                    checkbox.checked = false;
//                })
//
//                //TODO: Write a function that refreshes the file-table, put it here
//
//            } else {
//                console.log("Download canceled");
//            }
//        } else {
//            alert("No Files Selected To Download.");
//        }
//    }
}
// Register custom element
customElements.define("wibl-file-table", WIBLFileTable);
