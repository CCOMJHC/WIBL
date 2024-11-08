
const HEADERS = ["File Id", "Processed Time", "Update Time", "Notify Time", "Logger", "Platform", "Size"
    , "Observations", "Soundings", "Start Time", "End Time", "Status", "Messages"]

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

        // Apply external styles to the shadow dom
        const linkElem = document.createElement("link");
        linkElem.setAttribute("rel", "stylesheet");
        linkElem.setAttribute("href", this._styleUrl);
        shadow.appendChild(linkElem);

        const definitionList = document.createElement("dl");
        definitionList.setAttribute("id", "wc-wibl-detail-List");
        definitionList.className = "dl";
        HEADERS.forEach((header) => {
            const dt = document.createElement("dt");
            dt.textContent = header;
            const dd = document.createElement("dd");
            dd.setAttribute("id", header);
            dd.textContent = "";
            definitionList.appendChild(dt);
            definitionList.appendChild(dd);
        });
        shadow.appendChild(definitionList);

        function wiblDetailTableListWIBLDetails(message){
                const wiblFile = message.message;

                shadow.getElementById("File Id").textContent = wiblFile.fileid;
                shadow.getElementById("Processed Time").textContent = wiblFile.processtime;
                shadow.getElementById("Update Time").textContent = wiblFile.updatetime;
                shadow.getElementById("Notify Time").textContent = wiblFile.notifytime;
                shadow.getElementById("Logger").textContent = wiblFile.logger;
                shadow.getElementById("Platform").textContent = wiblFile.platform;
                shadow.getElementById("Size").textContent = wiblFile.size;
                shadow.getElementById("Observations").textContent = wiblFile.observations;
                shadow.getElementById("Soundings").textContent = wiblFile.soundings;
                shadow.getElementById("Start Time").textContent = wiblFile.starttime;
                shadow.getElementById("End Time").textContent = wiblFile.endtime;
                shadow.getElementById("Status").textContent = wiblFile.status;
                shadow.getElementById("Messages").textContent = wiblFile.messages;
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
