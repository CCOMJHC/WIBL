
const output_headers = ["File ID", "Processed time"]
const input_headers = ["fileid", "processtime", "platform", "logger", "starttime", "endtime"]

import { FileTable } from './FileTable.js';

export class WIBLFileTable extends FileTable {
    constructor() {
        super();
        this._inputHeaders = input_headers;
        this._outputHeaders = output_headers;
        this._fileType = "wibl";
    }

    connectedCallback() {
        super.connectedCallback();
    }

    // Resets every rows class so they are visible.
    // Hide the message that shows if there was a search that returned no results.
    clearCSS() {
        const table_rows = this._shadow.querySelectorAll("tr");

        const hiddenMessage = document.querySelector("#filterErrorMessage");

        const table = document.querySelector("#wibl-file-table");
        table.setAttribute("class", "");

        hiddenMessage.textContent = "";
        hiddenMessage.setAttribute("class", "is-hidden");

        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            row.setAttribute("class", "");
        }
    }

    // Applies a "filter" to the table depending on the given arguments
    // Any row that does not pass the filter has their class changed to "is-hidden"
    filterTable(date, time, platform, logger) {

        // Reset previous filter
        this.clearCSS();

        // Grab the value of each attribute
        date = date.value;
        time = time.value;
        platform = platform.value;
        logger = logger.value;

        let dateInclude = true;
        let exactDateInclude = true;
        let platformInclude = true;
        let loggerInclude = true;

        let hideCount = 0;

        let dateObj;

        let errorFlag = false;
        let errorMessage = document.querySelector("#filterErrorMessage");

        // If an argument is left empty by the user, it is not considered during the search
        // Thus, it is not included

        if (date === "") {
            dateInclude = false;
            exactDateInclude = false;
        } else {
            if (time === "") {
                exactDateInclude = false;
            }
        }

        if (platform === "") {
            platformInclude = false;
        }

        if (logger === "") {
            loggerInclude = false;
        }

        if (exactDateInclude) {
            const dateStr = `${date}T${time}`
            dateObj = new Date(dateStr);
            if (dateObj == null) {
                errorMessage.innerHTML += "(Alert) Time/Date provided is invalid<br>"
                errorFlag = true;
                exactDateInclude = false;
                dateInclude = false;
            }
        } else if (dateInclude) {
            dateObj = new Date(date);
            if (dateObj == null) {
                errorMessage.innerHTML += "(Alert) Date provided is invalid<br>"
                errorFlag = true;
                dateInclude = false;
            }
        } else if (time !== "") {
            errorMessage.innerHTML += "(Alert) Time is not considered if a date is not also provided.<br>"
            errorFlag = true;
        }

        //List of rows to hide
        let hideRows = [];

        var rows = this._rawData;

        // Filter
        for (let i = 0; i < rows.length; i++) {

            // Question asked: Should this row be hidden?
            // All of these must be true or the row will be added to hiddenRows
            let dateMatch = false;
            let platformMatch = false;
            let loggerMatch = false;

            if (exactDateInclude) {
            // Does the date and time fall between the start and end time of a file?
                let starttime = rows[i][4];
                let endtime = rows[i][5];

                starttime = starttime.slice(0, 16);
                endtime = endtime.slice(0, 16);
                const startObj = new Date(starttime);
                const endObj = new Date(endtime);

                if ((startObj <= dateObj) && (dateObj <= endObj)) {
                    dateMatch = true;
                }
            } else if (dateInclude) {
                let starttime = rows[i][4];
                let endtime = rows[i][5];

                starttime = starttime.slice(0, 10);
                endtime = endtime.slice(0, 10);

                const startObj = new Date(starttime);
                const endObj = new Date(endtime);

                if ((startObj <= dateObj) && (dateObj <= endObj)) {
                    dateMatch = true;
                }
            } else {
                dateMatch = true;
            }

            if (platformInclude) {
            // Do the platform names match?
                let originPlatform = rows[i][2];
                if (originPlatform === platform) {
                    platformMatch = true;
                }
            } else {
                platformMatch = true;
            }

            if (loggerInclude) {
            // Do the logger names match?
                let originLogger = rows[i][3];
                if (originLogger === logger) {
                    loggerMatch = true;
                }
            } else {
                loggerMatch = true;
            }

            // If one or more flags are false, add the row to the list of hidden rows
            if (!(loggerMatch && platformMatch && dateMatch)) {
                hideCount++;
                hideRows.push(rows[i][0]);
            }
        }

        const table_rows = this._shadow.querySelectorAll("tr");

        // Apply CSS
        for (let i = 0; i < table_rows.length; i++) {
            const row = table_rows[i];
            hideRows.forEach((hideRow) => {
                if (row.id === hideRow) {
                    row.setAttribute("class", "is-hidden");
                }
            })
        }
        // If the amount of rows hidden is equal to the total number of rows, there are none visible.
        if (hideCount == rows.length) {
            errorMessage.innerHTML += "(Error) No results for selected filters.";
            errorFlag = true;

            // Hide the table so the column headers don't stay floating
            const table = document.querySelector("#wibl-file-table");
            table.setAttribute("class", "is-hidden");
        }

        // Un-hide the error message so it is displayed to the user.
        if (errorFlag == true) {
            errorMessage.setAttribute("class", "");
        }
    }
}
// Register custom element
customElements.define("wibl-file-table", WIBLFileTable);
