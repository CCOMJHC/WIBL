
// TODO: Add remaining headers...
const output_headers = ["File ID", "Processed time"]

const input_headers = ["fileid", "processtime", "platform", "logger", "starttime", "endtime"]

import { FileTable } from './FileTable.js';

class WIBLFileTable extends FileTable {
    constructor() {
        super();
        this._url = null;
        this._styleUrl = null;
        this._shadow = null;
        this._rawData = [];
        this._inputHeaders = input_headers;
        this._outputHeaders = output_headers;
        this._fileType = "wibl";
    }

    connectedCallback() {
        super.connectedCallback();
    }

    clearCSS() {
        const table_rows = this._shadow.querySelectorAll("tr");

        const hiddenMessage = document.querySelector("#emptyMessage");
        hiddenMessage.setAttribute("class", "is-hidden");

        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            row.setAttribute("class", "");
        }
    }

    // This function works by finding all elements that should be HIDDEN, as in not a part of the table after the filter.
    filterTable(date, time, platform, logger) {

        // Reset previous filter
        this.clearCSS();

        date = date.value;
        time = time.value;
        platform = platform.value;
        logger = logger.value;

        let dateInclude = true;
        let platformInclude = true;
        let loggerInclude = true;

        let hideCount = 0;

        let dateObj;

        if (date === "") {
            dateInclude = false;
        } else {
            const dateStr = `${date}T${time}`
            dateObj = new Date(dateStr);
        }

        if (platform === "") {
            platformInclude = false;
        }

        if (logger === "") {
            loggerInclude = false;
        }

        let files = [];
        var rows = this._rawData;

        // Filter
        for (let i = 0; i < rows.length; i++) {
            let dateMatch = false;
            let platformMatch = false;
            let loggerMatch = false;

            if (dateInclude) {
                let starttime = rows[i][4];
                let endtime = rows[i][5];

                starttime = starttime.slice(0, 16);
                endtime = endtime.slice(0, 16);
                const startObj = new Date(starttime);
                const endObj = new Date(endtime);

                if ((startObj < dateObj) && (dateObj < endObj)) {
                    dateMatch = true;
                }
            } else {
                dateMatch = true;
            }

            if (platformInclude) {
                let originPlatform = rows[i][2];
                if (originPlatform === platform) {
                    platformMatch = true;
                }
            } else {
                platformMatch = true;
            }

            if (loggerInclude) {
                let originLogger = rows[i][3];
                if (originLogger === logger) {
                    loggerMatch = true;
                }
            } else {
                loggerMatch = true;
            }

            if (!loggerMatch || !platformMatch || !dateMatch) {
                hideCount++;
                files.push(rows[i][0]);
            }
        }

        const table_rows = this._shadow.querySelectorAll("tr");

        // Apply CSS
        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            files.forEach((file) => {
                if (row.id === file) {
                    row.setAttribute("class", "is-hidden");
                }
            })
        }
        if (hideCount == rows.length) {
            let emptyMessage = document.querySelector("#emptyMessage");
            emptyMessage.setAttribute("class", "");
        }
    }
}
// Register custom element
customElements.define("wibl-file-table", WIBLFileTable);
