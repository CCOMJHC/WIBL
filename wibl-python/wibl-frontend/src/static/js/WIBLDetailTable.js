const output_Headers = ["File Id", "Processed Time", "Update Time", "Notify Time", "Logger", "Platform", "Size"
    , "Observations", "Soundings", "Start Time", "End Time", "Status", "Messages"];

const input_Headers = ["fileid", "processtime", "updatetime", "notifytime", "logger", "platform", "size"
            , "observations", "soundings", "starttime", "endtime", "status", "messages"];

import { DetailTable } from './DetailTable.js';

class WIBLDetailTable extends DetailTable {
    constructor() {
        super();
        this._fileType = "wibl";
        this._outputHeaders = output_Headers;
        this._inputHeaders = input_Headers;
    }
}

// Register custom element
customElements.define("wibl-detail-table", WIBLDetailTable);
