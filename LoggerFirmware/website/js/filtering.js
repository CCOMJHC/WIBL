function populateFilterTable(data) {
    let display = '';
    if (data.count == 0) {
        display = 'All';
    } else {
        for (let n = 0; n < data.count; ++n) {
            display += data.ids[n] + ' ';
        }
    }
    document.getElementById('n1k-filter-list').textContent = display;
}

function populatePGNTable(data) {
    let display = '';
    if (data.all) {
        display = 'All';
    } else if (data.count == 0) {
        display = 'None';
    } else {
        for (let n = 0; n < data.count; ++n) {
            display += data.ids[n] + ' ';
        }
    }
    document.getElementById('n2k-pgn-list').textContent = display;
}

function addFilter() {
    const rawID = document.getElementById('add-n1k-item').value;
    const filterID = rawID.toUpperCase();
    document.getElementById('add-n1k-item').value = '';
    sendCommand(`accept ${filterID}`).then((data) => {
        populateFilterTable(data);
    });
}

function addPGN() {
    const rawPGN = document.getElementById('add-n2k-item').value;
    document.getElementById('add-n2k-item').value = '';
    sendCommand(`pgn ${rawPGN}`).then((data) => {
        populatePGNTable(data);
    });
}

function addAll() {
    sendCommand('pgn all').then((data) => {
        populatePGNTable(data);
    });
}

function clearFilterList() {
    sendCommand('accept all').then((data) => {
        populateFilterTable(data);
    });
}

function clearPGNList() {
    sendCommand('pgn clear').then((data) => {
        populatePGNTable(data);
    });
}

function bootstrapFilterTables() {
    const n1kboot = () => {
        sendCommand('accept').then((data) => {
            populateFilterTable(data);
        });
    }
    after(250, n1kboot);
    const n2kboot = () => {
        sendCommand('pgn').then((data) => {
            populatePGNTable(data);
        });
    }
    after(500, n2kboot);
}
