
/**
*   A reusable class that builds a Custom HTML Element depending on initialized values.
*   @extends {HTMLElement}
*/
export class DetailTable extends HTMLElement {
    constructor() {
        super();
        this._url = null;
        this._styleUrl = null;
        this._shadow = null;
        this._active = {value : false};
        this._fileType = null;
        this._outputHeaders = null;
        this._inputHeaders = null;
    }

    static observedAttributes = ["url", "stylesheet"];

    connectedCallback() {
        console.log(`${this._fileType}-detail-table: Added to page.`);
        const wsType = this._fileType;
        const wsURL = this._url + wsType + "/detail";
        const sock = SocketManager.getInstance(wsURL, wsType);

        // Create shadow DOM root
        const shadow = this.attachShadow({mode: "open"});
        this._shadow = shadow;

        // Apply external styles to the shadow dom
        const linkElem = document.createElement("link");
        linkElem.setAttribute("rel", "stylesheet");
        linkElem.setAttribute("href", this._styleUrl);
        shadow.appendChild(linkElem);

        const detailTable = document.createElement("table");
        detailTable.setAttribute("id", `${this._fileType}-detail-table`);
        detailTable.className = "table is-fullwidth";
        shadow.appendChild(detailTable);

        // Create default view
        const defaultText = document.createElement("div");
        defaultText.setAttribute("id", "defaultText");
        defaultText.textContent = "To view details select a row!";
        shadow.appendChild(defaultText);

        // Generate variables to be used in ListFileDetails scope
        let fileType = this._fileType;
        let inputHeaders = this._inputHeaders;
        let outputHeaders = this._outputHeaders;
        let output_count = outputHeaders.length;
        let input_count = inputHeaders.length;
        let active = this._active;

        function listFileDetails(message) {
            function formatStatus(header, content) {
                if (header === "Status") {
                    switch(content) {
                        case 0:
                            return "Processing Started";
                        case 1:
                            return "Processing Successful";
                        case 2:
                            return "Processing Failed";
                        default:
                            return "Unknown";
                    }
                } else if (header === "Validation Status") {
                    const x = content & 0x7;
                    switch(x) {
                        case 0x1:
                            return  "Validation Started";
                        case 0x2:
                            return "Validation Successful";
                        case 0x4:
                            return "Validation Failed";
                        default:
                            return "Validation Status Unknown";
                    }
                } else if (header === "Upload Status") {
                    const x = content & 0x38
                    switch(x) {
                        case 0x8:
                            return "Upload Started";
                        case 0x10:
                            return "Upload Successful";
                        case 0x20:
                            return "Upload Failed";
                        default:
                            return "Upload Status Unknown";
                    }
                } else if (header === "State") {
                    switch(content) {
                        case 0:
                            return "Online";
                        case 1:
                            return "Deleted";
                        case 2:
                            return "Archived";
                        default:
                            return "Unknown";
                    }
                } else {
                    return content;
                }
            }

            console.log("In listFileDetails...");
            const table = shadow.getElementById(`${fileType}-detail-table`);
            const messageFile = message.message;

            if (active.value === true) {
                for (let i = 0; i < output_count; i++) {
                    const td = shadow.getElementById(outputHeaders[i]);
                    td.textContent = formatStatus(outputHeaders[i], messageFile[inputHeaders[i]]);
                }
            } else {
                shadow.getElementById("defaultText").classList.add("is-hidden")
                const thead = document.createElement("thead");
                const headerRow = document.createElement("tr");
                const header1 = document.createElement("th");
                const header2 = document.createElement("th");

                header1.textContent = "Type";
                header2.textContent = "Data";

                headerRow.appendChild(header1);
                headerRow.appendChild(header2);
                thead.appendChild(headerRow);
                table.appendChild(thead);

                const tbody = document.createElement("tbody");
                for (let i = 0; i < output_count; i++) {
                    const row = document.createElement("tr");
                    const td1 = document.createElement("td");
                    td1.textContent = outputHeaders[i];
                    const td2 = document.createElement("td");
                    const result = formatStatus(outputHeaders[i], messageFile[inputHeaders[i]])
                    td2.textContent = result;
                    td2.setAttribute("id", outputHeaders[i]);
                    row.appendChild(td1);
                    row.appendChild(td2);
                    tbody.appendChild(row);
                }
                table.appendChild(tbody);
            }
            active.value = true;
        }
        sock.addHandler(`list-${fileType}-details`, listFileDetails);
    }

    disconnectedCallback() {
        console.log(`${this._fileType}-detail-table: Removed from page.`);
    }

    adoptedCallback() {
        console.log(`${this._fileType}-detail-table: Moved to new page.`);
    }

    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`${this._fileType}-detail-table: Attribute ${name} has changed from ${oldValue} to ${newValue}.`);
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

    clear() {
        const table = this._shadow.getElementById(`${this._fileType}-detail-table`);
        table.innerHTML = "";
        this._active.value = false;
        const defaultText = this._shadow.getElementById("defaultText");
        defaultText.textContent = "No Linked File";
        defaultText.classList.remove("is-hidden");
    }
}

