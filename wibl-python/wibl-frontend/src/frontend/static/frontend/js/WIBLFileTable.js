
// TODO: Add remaining headers...
const HEADERS = ["File ID", "Processed time"]

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
        const wsURL = this._url + wsType + "/";
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
                // TODO: Add remaining fields later...
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
}

// Register custom element
customElements.define("wibl-file-table", WIBLFileTable);
