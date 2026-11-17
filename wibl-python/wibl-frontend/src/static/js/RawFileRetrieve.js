
// Static class created for the retrieval and display of Geojson Files
export class RawFileRetrieve {

    /*
     * Find the table row that is selected, then calls to the manager
     * to grab the json contained in the file.
     * Returns an promise of the json contained in the manager response.
    */
    static async retrieve() {
        const geojsonFileTable = document.getElementById("geojson-file-table");
        const selectedRow = geojsonFileTable._shadow.querySelector("tr.is-selected");
        if (!selectedRow) throw new Error("No row is selected.");

        const tableData = selectedRow.querySelector("td");
        if (!tableData) throw new Error("Selected row does not contain a <td> element.");

        const fileid = tableData.id;

        const res = await fetch(`./saveGeojsonFile/${fileid}`);
        if (res.ok) {
            const geojsonObject = await res.json();
            return geojsonObject;
        } else {
            alert("Could not retrieve raw file.")
            return null;
        }
    }

    // Write the contents of the provided jsonObject to an html element.
    static apply(jsonObject) {
        const json_display = document.getElementById("geojsonFileContent");
        json_display.textContent = JSON.stringify(jsonObject, null, 2);
    }
}