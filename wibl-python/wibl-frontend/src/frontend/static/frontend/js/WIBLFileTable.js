import { ActiveTable } from "activetable";

class WIBLFileTable extends ActiveTable {
    constructor() {
        super();
    }

    connectedCallback() {
        console.log("wibl-file-table: Added to page.");
        super.connectedCallback();
    }

    disconnectedCallback() {
        console.log("wibl-file-table: Removed from page.");
        super.disconnectedCallback();
    }

    adoptedCallback() {
        console.log("wibl-file-table: Moved to new page.");
        super.adoptedCallback();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`wibl-file-table: Attribute ${name} has changed from ${oldValue} to ${newValue}.`);
        super.attributeChangedCallback(name, oldValue, newValue);
    }
}

// Register custom element
customElements.define("wibl-file-table", WIBLFileTable);