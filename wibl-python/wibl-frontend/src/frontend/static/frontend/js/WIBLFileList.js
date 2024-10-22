// Rudimentary Web Component showing how to load and display manager data received
// via WebSocket. We will probably want to adapt this into a table view and/or extend
// an existing Web Component such as smart-table (https://github.com/HTMLElements/smart-table).
//
// CSS Stylesheet for this component should be stored in ../css/WIBLFileList.css and passed
// in via the `styleshee` attribute:
//
//      <wibl-file-list id="wibl-file-list1"
//                      url="{{ wsURL }}"
//                      stylesheet="{% static 'frontend/css/WIBLFileList.css' %}">
//      </wibl-file-list>
//
// Documentation for creating/editing Web Components can be found on MDN
// (https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements).
// and at WHATWG (https://html.spec.whatwg.org/multipage/custom-elements.html).

class WIBLFileList extends HTMLElement {
    constructor() {
        // Always call super first
        super();
        this._url = null;
        this._styleUrl = null;
        this._shadow = null;
    }

    static observedAttributes = ["url", "stylesheet"];

    // connectedCallback: Called each time the element is added to the document.
    // The specification recommends that, as far as possible, developers should
    // implement custom element setup in this callback rather than the constructor.
    connectedCallback() {
        console.log("wibl-file-list: Custom element added to page.");
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

        // Create ul to hold list items
        const ul = document.createElement("ul");
        ul.setAttribute("id", "wc-wibl-file-list");
        ul.className = "class-1"
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
    //
    // Note: When adding an attribute, make sure to also added it to the `observedAttributes` list above.
    //
    // See [Responding to attribute changes](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements#responding_to_attribute_changes)
    // for more details about this callback.
    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`wibl-file-list: Attribute ${name} has changed from ${oldValue} to ${newValue}.`);
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

    exampleOutsideEventReactivity() {
        console.log("exampleOutsideEventReactivity() called...");
        const ul = this._shadow.getElementById("wc-wibl-file-list");
        switch (ul.className) {
            case "class-1":
                ul.className = "class-2";
                break;
            case "class-2":
                ul.className = "class-1";
                break;
            default:
                ul.className = "class-2";
        }
    }
}

// Register custom element
customElements.define("wibl-file-list", WIBLFileList);
