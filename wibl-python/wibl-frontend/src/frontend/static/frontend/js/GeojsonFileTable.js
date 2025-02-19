const output_headers = ["File ID", "Upload Time"]
const input_headers = ["fileid", "uploadtime", "updatetime", "notifytime",
    "logger", "size", "soundings", "status", "messages"]
import { FileTable } from './FileTable.js';

class GeojsonFileTable extends FileTable {
    constructor() {
        super();
        this._inputHeaders = input_headers;
        this._outputHeaders = output_headers;
        this._fileType = "geojson";
    }

    connectedCallback() {
        super.connectedCallback();
    }
}
// Register custom element
customElements.define("geojson-file-table", GeojsonFileTable);
