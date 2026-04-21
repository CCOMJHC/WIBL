
/**
*   A reusable class that builds a Custom HTML Element depending on initialized values.
*   @extends {HTMLElement}
*/
export class FileTable extends HTMLElement {

    /*
        For correct connectedCallback() functionality, an extending class must have the following
        initialized attributes in their constructor. Created for code sharing between Wibl and geoJSON implementation.

        _outputHeaders:
            A list of header names that directly correspond to the table's headers. Expected First element to be a
            heading for File ID. Must be smaller than or equal to the size of input headers. Having matching indexes
            between input and output headers is essential, because the data directly corresponds to the header index.

        _inputHeaders:
            A list of headers that directly correspond with the JSON response from the manager. Used to populate
            the table as well as the classes _rawData. Must be greater than or equal to the size of the _output_headers
            argument. Anything not included in the output headers is only stored in raw data for search filtering purposes.

        _fileType:
            Either “wibl” or “geojson”. Used interchangeably throughout all functions in the table. Used when creating
            the socket URL as well as crafting the correct manager endpoint to get data from.


        Example:
           const output_headers = ["File ID"]
           const input_headers = ["file_id", "processtime", "loggername", etc.] (Whatever key that data is associated with in the response)
           const file_type = "png" (Only ever actually "wibl" or "geojson")
           class pngTable extends FileTable {
                constructor() {
                    super();
                    this._outputHeaders = output_headers;
                    this._inputHeaders = output_headers;
                    this._fileType = "png"
                }

                (Any other required functionality, search/filter features, etc.)
           }

       This class will create a table with two columns, one with the header "File ID" and another with a blank header.
       Each row will be a different file from the manager with the corresponding input header set at the value.
       The blank header column will contain an auto generated checkbox associated with the file contained in that row.
       Checkboxes ensure delete and download functionality no matter what output headers are given to the child class.
       An instance of pngTable class will contain an attribute named _rawData. Depending on the given input headers, this
       2d array will update with the information grabbed from each key in the list.
    */


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
        const wsURL = this._url + this._fileType + "/table";
        const sock = SocketManager.getInstance(wsURL, this._fileType);

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
        table.setAttribute("id", `wc-${this._fileType}-file-table`);
        table.className = "table";

        // Create table container
        const tableContainer = document.createElement("div");
        tableContainer.className = "table-container";
        tableContainer.setAttribute("id", `${this._fileType}-table-container`);
        tableContainer.appendChild(table);
        tableContainer.setAttribute("style", "max-height: 20rem; overflow-y: auto;");
        shadow.appendChild(tableContainer);

        // Generate variables to be used in ListFiles scope
        let raw = this._rawData;
        let fileType = this._fileType;
        let output_headers = this._outputHeaders;
        let input_headers = this._inputHeaders;
        let output_count = this._outputHeaders.length;
        let input_count = this._inputHeaders.length;

        function ListFiles(message) {
            console.log(`In ListFiles for table of type: ${fileType}`);
            const table = shadow.getElementById(`wc-${fileType}-file-table`);

            // Wipes table/raw data to allow for reload
            table.innerHTML = "";
            raw.length = 0;

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

            // Append header row to table
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

                // Iterate through the given output headers, skipping the fileid column
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
            document.dispatchEvent(new CustomEvent("linkFilesEvent"));
        }

        // Bare bones socket handler, most of the delete work is handled by the manager.
        function DeleteFiles(message) {
            console.log(`Successfully Deleted Files \n${message['message'].join('\n')}`);
        }

        sock.addHandler(`delete-${this._fileType}-files`, DeleteFiles);
        sock.addHandler(`list-${this._fileType}-files`, ListFiles);
    }

    // Returns a list of rows that have their checkbox checked
    // Option changes certain log messages depending on functionality.
    // 0: delete
    // 1: download
    // 2: map
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
                return selectedNames;
            }

            if (confirm(promptText)) {
                //uncheck all boxes
                checkedBoxes.forEach(checkbox => {
                    checkbox.checked = false;
                })

                return selectedNames;
            } else {
                console.log("Delete canceled");
                return;
            }
        } else {
            return selectedNames;
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
