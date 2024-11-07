
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

        document.addEventListener("fileSelected", (event) => {
            const { fileId, ProcessedTime, UpdateTime, NotifyTime, Logger, Platform, Size, Observations, Soundings, StartTime, EndTime, Status, Messages } = event.detail;
            this._shadow.getElementById("File Id").textContent = event.detail.fileid;
            this._shadow.getElementById("Processed Time").textContent = event.detail.processedtime;
            this._shadow.getElementById("Update Time").textContent = event.detail.updatetime;
            this._shadow.getElementById("Notify Time").textContent = event.detail.notifytime;
            this._shadow.getElementById("Logger").textContent = event.detail.logger;
            this._shadow.getElementById("Platform").textContent = event.detail.platform;
            this._shadow.getElementById("Size").textContent = event.detail.size;
            this._shadow.getElementById("Observations").textContent = event.detail.observations;
            this._shadow.getElementById("Soundings").textContent = event.detail.soundings;
            this._shadow.getElementById("Start Time").textContent = event.detail.starttime;
            this._shadow.getElementById("End Time").textContent = event.detail.endtime;
            this._shadow.getElementById("Status").textContent = event.detail.status;
            this._shadow.getElementById("Messages").textContent = event.detail.messages;
        });
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
