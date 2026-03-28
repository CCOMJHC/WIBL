function populateDisplay(data) {
    const msgs = data.messages || [];
    document.getElementById('token-display').textContent =
        (msgs[0] === undefined || msgs[0] === '') ? 'Not set' : msgs[0];
    document.getElementById('cert-output').innerHTML =
        (msgs[1] === undefined || msgs[1] === '') ? 'Not set' : msgs[1];
    const dropboxEl = document.getElementById('dropbox-token-display');
    if (dropboxEl) {
        dropboxEl.textContent =
            (msgs[2] === undefined || msgs[2] === '') ? 'Not set' : msgs[2];
    }
}

function resetToken() {
    const token = document.getElementById('add-item').value;
    document.getElementById('add-item').value = '';
    sendCommand(`auth token ${token}`).then((data) => {
        populateDisplay(data);
    });
}

function resetDropboxToken() {
    const token = document.getElementById('dropbox-token-input').value;
    document.getElementById('dropbox-token-input').value = '';
    sendCommand(`auth dropbox ${token}`).then((data) => {
        populateDisplay(data);
    });
}

async function testDropboxUpload() {
    const el = document.getElementById('dropbox-test-result');
    if (el) {
        el.textContent = 'Uploading test file…';
    }
    const url = 'http://' + location.host + '/command';
    const data = new FormData();
    data.append('command', 'dropbox test');
    try {
        const response = await fetch(url, { method: 'POST', body: data });
        const body = await response.json();
        const msgs = body.messages || [];
        const text = msgs.length ? msgs.join(' | ') : 'No response message.';
        if (el) {
            el.textContent = response.ok ? text : ('HTTP ' + response.status + ': ' + text);
        }
    } catch (e) {
        if (el) {
            el.textContent = 'Request failed (network or invalid JSON).';
        }
    }
}

function onCertUpload() {
    const selectedFile = document.getElementById('cert-file').files[0];
    let contents = new FileReader();
    contents.readAsText(selectedFile);
    contents.onerror = function() {
        console.log(contents.error);
        window.alert('Failed on load: ' + contents.error.message);
    }
    contents.onload = function() {
        sendCommand('auth cert ' + contents.result).then((data) => {
            populateDisplay(data);
        });
    }
}

function bootstrapAuthentication() {
    const boot = () => {
        sendCommand('auth').then((data) => {
            populateDisplay(data);
        });
    }
    after(500, boot);
}
