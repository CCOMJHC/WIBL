
// TODO: Add remaining headers...
const HEADERS = ["File ID", "Processed time", ""]

class WIBLFileTable extends HTMLElement {
    constructor() {
        super();
        this._url = null;
        this._styleUrl = null;
        this._shadow = null;
    }

    static observedAttributes = ["url", "stylesheet"];

    connectedCallback() {
        console.log("wibl-file-table: Added to page.");
        const wsType = "wibl";
        const wsURL = this._url + wsType + "/table";
        const sock = SocketManager.getInstance(wsURL, wsType);

        // Create shadow DOM root
        const shadow = this.attachShadow({mode: "open"});
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

        function WIBLFileTableHanlderListWiblFiles(message) {
            // TODO: Delete existing content in table to support re-loading of data.
            console.log("In WIBLFileTableHanlderListWiblFiles...");
            const table = shadow.getElementById("wc-wibl-file-table");
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
            for (const wiblFile of message.message.files) {
                const row = document.createElement("tr");

                // fileid field
                const fileName = wiblFile.fileid;
                console.log(`Filename: ${fileName}`);
                var td = document.createElement("td");
                td.setAttribute("id", `wc-wibl-file-${fileName}`);
                td.textContent = fileName;
                row.appendChild(td);
                // processtime field
                td = document.createElement("td");
                td.textContent = wiblFile.processtime;
                row.appendChild(td);
                var td2 = document.createElement("td");

                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.className = "row-checkbox";
                td2.appendChild(checkbox);
                row.appendChild(td2);
                // TODO: Add remaining fields later...
                row.setAttribute("id", fileName);
                tbody.appendChild(row);
            }
            table.appendChild(tbody);
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

    searchDate(date) {
        if (date === "") {
            console.log("No date selected");
        } else {
            const dateObj = new Date(date);
            const searchYear = dateObj.getFullYear();
            const searchMonth = dateObj.getMonth() + 1;
            const searchDay = dateObj.getDate();

            //Figure out how to itterate over an HTML collection
            var rows = this._shadow.children[1].rows;
            var dates = [];
            for (let i = 1; i <= rows.length; i++) {
                let tempDate = rows[i].querySelector('td:nth-of-type(2)');
                let tempTrunk = tempDate.textcontent.replace(/\.\d{3}\d*/, (match) => match.slice(0, 4));
                const tempDateObj = new Date(tempTrunk);
                const year = tempDateObj.getFullYear();
                const month = tempDateObj.getMonth() + 1;
                const day = tempDateObj.getDate();

                if (searchDay == day && searchMonth == month && searchYear == year) {
                    dates.push(tempDate);
                }
            }
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
