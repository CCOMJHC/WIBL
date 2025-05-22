/* onUpload() is used to extract the file for metadata that the user has specified in the
 * input element, and loads the contents for transmission to the logger.
*/
function onUpload() {
    const selectedFile = document.getElementById("metadata").files[0];
    let contents = new FileReader();
    contents.readAsText(selectedFile);
    contents.onerror = function() {
        console.log(contents.error);
        window.alert('Failed on read: ' + contents.error.message);
    }
    contents.onload = function() {
        try {
            let dict = JSON.parse(contents.result);
            let mapDict = JSON.stringify(dict);
            sendCommand('metadata ' + mapDict).then((data) => {
                mapDict = JSON.stringify(data, null, 2);
                document.getElementById("metadata-output").innerHTML = mapDict;
            });
        } catch (error) {
            console.error(error);
            window.alert('Failed to upload JSON: ' + error.message);
        }
    }
}

function bootstrapMetadata() {
    const boot = () => {
        sendCommand('metadata').then((data) => {
            document.getElementById('metadata-output').textContent = JSON.stringify(data, null, 2);
        });
    }
    after(500, boot);
}
