const output_Headers = ["File ID", "Upload Time", "Update Time", "Notify Time", "Logger", "Size", "Soundings",
"Validation Status", "Upload Status", "Messages", "State"];

const input_Headers = ["fileid", "uploadtime", "updatetime", "notifytime",
    "logger", "size", "soundings", "status", "status", "messages", "state"]

import { DetailTable } from './DetailTable.js';

class GeojsonDetailTable extends DetailTable {
    constructor() {
        super();
        this._fileType = "geojson";
        this._outputHeaders = output_Headers;
        this._inputHeaders = input_Headers;
    }
}

// Register custom element
customElements.define("geojson-detail-table", GeojsonDetailTable);
