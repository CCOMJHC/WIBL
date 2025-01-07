
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
                let j = 0;
                for (const wiblFile of message.message.files){
                    for (let i = 0; i < (HEADERS.length - 1) ; i++) {
                        const td = rows[j].querySelector(`td:nth-of-type(${(i + 1)})`);
                        td.textContent = wiblFile[input_headers[i]];
                    }

                    raw[j][0] = wiblFile.fileid;
                    raw[j][1] = wiblFile.processtime;
                    raw[j][2] = wiblFile.platform;
                    raw[j][3] = wiblFile.logger;
                    j++;
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

                    data[2] = wiblFile.platform;
                    data[3] = wiblFile.logger;

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


    // This function works by finding all elements that should be HIDDEN, as in not a part of the table after the filter.
    filterTable(date, platform, logger) {

        // Reset previous filter
        const table_rows = this._shadow.querySelectorAll("tr");

        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            row.setAttribute("class", "");
        }

        date = date.value;
        platform = platform.value;
        logger = logger.value;

        let dateInclude = true;
        let platformInclude = true;
        let loggerInclude = true;

        let searchYear = 0;
        let searchMonth = 0;
        let searchDay = 0;

        if (date === "") {
            dateInclude = false;

        } else {
            const dateObj = new Date(date);
            searchYear = dateObj.getFullYear();
            searchMonth = dateObj.getMonth() + 1;
            searchDay = dateObj.getDate();
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
                let originDate = rows[i][1];
                let concatDate = originDate.slice(0, 10)
                const compairDate = new Date(concatDate);

                if (searchDay == compairDate.getDate() || searchMonth == (compairDate.getMonth() + 1) || searchYear == compairDate.getYear()) {
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
                files.push(rows[i][0]);
            }
        }

        // Apply CSS
        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            files.forEach((file) => {
                if (row.id === file) {
                    row.setAttribute("class", "is-hidden");
                }
            })
        }
    }

    deleteSelectedFiles() {
        console.log("deleteSelectedFiles() called...");

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
            const promptText = `Would you like to delete files: \n${selectedNames.join('\n')}?`;
            if (confirm(promptText)) {
                //TODO: Communicate with manager to delete files selected
                console.log(`Delete Files: ${selectedNames.join(', ')}`);

                //uncheck all boxes
                checkedBoxes.forEach(checkbox => {
                    checkbox.checked = false;
                })

                //TODO: Write a function that refreshes the file-table, put it here

            } else {
                console.log("Delete canceled");
            }
        } else {
            alert("No Files Selected To Delete.");
        }
    }

    archiveSelectedFiles() {
        console.log("archiveSelectedFiles() called...");

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
            const promptText = `Would you like to archive files: ${selectedNames.join('\n')}?`;
            if (confirm(promptText)) {
                //TODO: Communicate with manager to archive files selected
                console.log(`Selected Files: ${selectedNames.join(', ')}`);

                //uncheck all boxes
                checkedBoxes.forEach(checkbox => {
                    checkbox.checked = false;
                })

                //TODO: Write a function that refreshes the file-table, put it here

            } else {
                console.log("Archive canceled");
            }
        } else {
            alert("No Files Selected To Archive.");
        }
    }
}
// Register custom element
customElements.define("wibl-file-table", WIBLFileTable);
