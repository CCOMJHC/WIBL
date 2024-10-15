// Rudimentary Web Component showing how to load and display manager data received
// via WebSocket. We will probably want to adapt this into a table view and/or extend
// an existing Web Component such as smart-table (https://github.com/HTMLElements/smart-table).
//
// Documentation for creating/editing Web Components can be found on MDN
// (https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements).
// and at WHATWG (https://html.spec.whatwg.org/multipage/custom-elements.html).

class WIBLFileList extends HTMLElement {
    constructor() {
        // Always call super first
        super();
        this._url = null;
    }

    static observedAttributes = ["url"];

    // connectedCallback: Called each time the element is added to the document.
    // The specification recommends that, as far as possible, developers should
    // implement custom element setup in this callback rather than the constructor.
    connectedCallback() {
        console.log("wibl-file-list: Custom element added to page.");
        const wsType = "wibl";
        const wsURL = this._url + wsType + "/";
        const sock = SocketManager.getInstance(wsURL, wsType);

        // Create shadow DOM root
        const shadow = this.attachShadow({ mode: "open" });
        // Create ul to hold list items
        const ul = document.createElement("ul");
        ul.setAttribute("id", "wc-wibl-file-list");
        shadow.appendChild(ul);

        // Create event handler callback and register it with SocketManager
        function WIBLFileListHandlerListWiblFiles(message) {
            console.log("In WIBLFileListHandlerListWiblFiles...");
            const wiblFileList = shadow.getElementById("wc-wibl-file-list");
            for (const wiblFile of message.message.files) {
                const fileName = wiblFile.fileid;
                console.log(`Filename: ${fileName}`);
                const li = document.createElement("li");
                li.setAttribute("id", `wc-wibl-file-${fileName}`);
                li.textContent = fileName;
                wiblFileList.appendChild(li);
            }
        }
        sock.addHandler("list-wibl-files", WIBLFileListHandlerListWiblFiles);

        // Request WIBL file data from the WebSocket
        sock.sendRequest("list-wibl-files");
    }

    // disconnectedCallback: Called each time the element is removed from the
    // document.
    disconnectedCallback() {
        console.log("wibl-file-list: Removed from page.");
    }

    // adoptedCallback: Called each time the element is moved to a new document.
    adoptedCallback() {
        console.log("wibl-file-list: Moved to new page.");
    }

    // attributeChangedCallback: Called when attributes are changed, added, removed,
    // or replaced.
    // See [Responding to attribute changes](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements#responding_to_attribute_changes)
    // for more details about this callback.
    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`wibl-file-list: Attribute ${name} has changed from ${oldValue} to ${newValue}.`);
        switch(name) {
            case "url":
                // URL should only be set on initialization since there is currently
                // not logic for
                this._url = newValue;
                break;
            default:
                console.warn(`Unknown attribute ${name}`);
        }
  }
}

// Register custom element
customElements.define("wibl-file-list", WIBLFileList);
