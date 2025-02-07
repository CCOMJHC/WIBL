
export class FileTable extends HTMLElement {
    constructor() {
        super();
        this._url = null;
        this._styleUrl = null;
        this._shadow = null;
        this._rawData = [];
        this._fileType = null;
        this._outputHeaders = [];
        this._inputHeaders = [];
    }

    static observedAttributes = ["url", "stylesheet"];

    connectedCallback() {
        console.log(`${this._fileType}-file-table: Added to page.`);
        const wsType = this._fileType;
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
        table.setAttribute("id", `wc-${wsType}-file-table`);
        table.className = "table";
        shadow.appendChild(table);

        let raw = this._rawData;
        let fileType = this._fileType;
        let output_headers = this._outputHeaders;
        let input_headers = this._inputHeaders;
        let output_count = this._outputHeaders.length;
        let input_count = this._inputHeaders.length;


        function ListFiles(message) {
            console.log(`In ListFiles for table of type: ${fileType}`);
            const table = shadow.getElementById(`wc-${fileType}-file-table`);

            // Create header row
            const thead = document.createElement("thead");
            const headerRow = document.createElement("tr");

            // Fill in the headers
            for (const headerText of output_headers) {
                const header = document.createElement("th");
                header.textContent = headerText;
                headerRow.appendChild(header);
            }

            // Add the checkbox header
            const header = document.createElement("th");
            header.textContent = "";
            headerRow.appendChild(header);

            headerRow.setAttribute("class", "headerRow");
            thead.appendChild(headerRow)
            table.appendChild(thead);

            // Load file fields into table
            const tbody = document.createElement("tbody");
            let i = 0
            for (const file of message.message.files) {
                let data = [];
                const row = document.createElement("tr");

                // fileid field
                const fileName = file.fileid;
                var td = document.createElement("td");
                td.setAttribute("id", `${fileName}`);
                td.textContent = fileName;
                row.appendChild(td);

                // Iterate through the given output headers
                for (let x = 1; x < output_count; x++) {
                    td = document.createElement("td");
                    td.textContent = file[input_headers[x]];
                    row.appendChild(td);
                }

                // Add given input headers to data, later added to the tables raw data 2d array
                for (let y = 0; y < input_count; y++) {
                    data[y] = file[input_headers[y]];
                }

                // Create this rows checkbox
                var td = document.createElement("td");
                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.className = "row-checkbox";
                td.appendChild(checkbox);
                row.appendChild(td);
                row.setAttribute("id", fileName);

                tbody.appendChild(row);
                raw[i] = data;
                i++;
            }
            table.appendChild(tbody);
        }

        function DeleteFiles(message) {
            console.log(`Successfully Deleted Files \n${message['message'].join('\n')}`);
        }

        sock.addHandler(`delete-${this._fileType}-files`, DeleteFiles);
        sock.addHandler(`list-${this._fileType}-files`, ListFiles);
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

    disconnectedCallback() {
        console.log(`${this._fileType}-file-table: Removed from page.`);
    }

    adoptedCallback() {
        console.log(`${this._fileType}-file-table: Moved to new page.`);
    }

    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`${this._fileType}-file-table: Attribute ${name} has changed from ${oldValue} to ${newValue}.`);
        switch (name) {
            case "url":
                this._url = newValue;
                break;
            case "stylesheet":
                this._styleUrl = newValue;
                break;
            default:
                console.warn(`Unknown attribute ${name}`);
        }
    }
}
