
export class RawFileRetrieve {

    static async retrieve() {
        const geojsonFileTable = document.getElementById("geojson-file-table");
        const selectedRow = geojsonFileTable._shadow.querySelector("tr.is-selected");
        if (!selectedRow) throw new Error("No row is selected.");

        const tableData = selectedRow.querySelector("td");
        if (!tableData) throw new Error("Selected row does not contain a <td> element.");

        const fileid = tableData.id;

        const res = await fetch(`./saveGeojsonFile/${fileid}`);
        if (!res.ok) {
            throw new Error(`HTTP error! Status: ${res.status}`);
        }

        const geojsonObject = await res.json();
        return geojsonObject;
    }

    static apply(jsonObject) {
        const json_display = document.getElementById("geojsonFileContent");
        json_display.textContent = JSON.stringify(jsonObject, null, 2);
    }
}