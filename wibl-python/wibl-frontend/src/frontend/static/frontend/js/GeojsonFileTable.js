const output_headers = ["File ID", "Upload Time"]
const input_headers = ["fileid", "uploadtime", "updatetime", "notifytime",
    "logger", "size", "soundings", "status", "messages"]
import { FileTable } from './FileTable.js';

export class GeojsonFileTable extends FileTable {
    constructor() {
        super();
        this._inputHeaders = input_headers;
        this._outputHeaders = output_headers;
        this._fileType = "geojson";
    }

    connectedCallback() {
        super.connectedCallback();
    }

    clearCSS() {
        const table_rows = this._shadow.querySelectorAll("tr");

        const hiddenMessage = document.querySelector("#filterErrorMessage");

        const table = document.querySelector("#geojson-file-table");
        table.setAttribute("class", "");

        hiddenMessage.textContent = "";
        hiddenMessage.setAttribute("class", "is-hidden");

        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            row.setAttribute("class", "");
        }
    }
}
// Register custom element
customElements.define("geojson-file-table", GeojsonFileTable);
