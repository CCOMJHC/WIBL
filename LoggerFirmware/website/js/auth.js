function populateDisplay(data) {
    if (data.messages[0] === '') {
        document.getElementById('token-display').textContent = 'Not set';
    } else {
        document.getElementById('token-display').textContent = data.messages[0];
    }
    if (data.messages[1] === '') {
        document.getElementById('cert-output').innerHTML = 'Not set';
    } else {
        document.getElementById('cert-output').innerHTML = data.messages[1];
    }
}

function resetToken() {
    const token = document.getElementById('add-item').value;
    document.getElementById('add-item').value = '';
    sendCommand(`auth token ${token}`).then((data) => {
        populateDisplay(data);
    });
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
