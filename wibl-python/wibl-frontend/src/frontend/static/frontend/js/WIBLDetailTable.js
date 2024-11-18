const output_Headers = ["File Id", "Processed Time", "Update Time", "Notify Time", "Logger", "Platform", "Size"
    , "Observations", "Soundings", "Start Time", "End Time", "Status", "Messages"];

const input_Headers = ["fileid", "processtime", "updatetime", "notifytime", "logger", "platform", "size"
            , "observations", "soundings", "starttime", "endtime", "status", "messages"];

const defText = "To view details select a row!";

class WIBLDetailTable extends HTMLElement {
    constructor() {
        super();
        this._url = null;
        this._styleUrl = null;
        this._shadow = null;
    }

    static observedAttributes = ["url", "stylesheet"];

    connectedCallback() {
        console.log("wibl-detail-table: Added to page.");
        const wsType = "wibl";
        const wsURL = this._url + wsType + "/detail";
        const sock = SocketManager.getInstance(wsURL, wsType);

        // Create shadow DOM root
        const shadow = this.attachShadow({mode: "open"});
        this._shadow = shadow;
        let active = 0;
        this._active = active;

        // Apply external styles to the shadow dom
        const linkElem = document.createElement("link");
        linkElem.setAttribute("rel", "stylesheet");
        linkElem.setAttribute("href", this._styleUrl);
        shadow.appendChild(linkElem);

        const detailTable = document.createElement("table");
        detailTable.setAttribute("id", "wibl-detail-table");
        detailTable.className = "table is-fullwidth";
        shadow.appendChild(detailTable);

        // Create default view
        const defaultText = document.createElement("div");
        defaultText.setAttribute("id", "defaultText");
        defaultText.textContent = defText;
        shadow.appendChild(defaultText);

        function wiblDetailTableListWIBLDetails(message){
            console.log("In WIBLDetailTableListWiblDetails...");
            const table = shadow.getElementById("wibl-detail-table");
            const wiblFile = message.message;
            if (active == 1) {
                for (let i = 0; i < output_Headers.length; i++) {
                    const td = shadow.getElementById(input_Headers[i]);
                    td.textContent = wiblFile[input_Headers[i]];
                }
            } else {
                shadow.getElementById("defaultText").remove();
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
                for (let i = 0; i < output_Headers.length; i++) {
                    const row = document.createElement("tr");
                    const td1 = document.createElement("td");
                    td1.textContent = output_Headers[i];
                    const td2 = document.createElement("td");
                    td2.textContent = wiblFile[input_Headers[i]];
                    td2.setAttribute("id", input_Headers[i]);
                    row.appendChild(td1);
                    row.appendChild(td2);
                    tbody.appendChild(row);
                }
            table.appendChild(tbody);
            }
            active = 1;
        };
        sock.addHandler("list-wibl-details", wiblDetailTableListWIBLDetails);
    }

    disconnectedCallback() {
        console.log("wibl-detail-table: Removed from page.");
    }

    adoptedCallback() {
        console.log("wibl-detail-table: Moved to new page.");
    }

    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`wibl-detail-table: Attribute ${name} has changed from ${oldValue} to ${newValue}.`);
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
customElements.define("wibl-detail-table", WIBLDetailTable);
