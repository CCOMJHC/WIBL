function roundSize(rawSize) {
    const rounded = Math.round(rawSize*100)/100;
    return rounded;
}

function translateSize(byteCount) {
    let dataSize;

    if (byteCount > 1024*1024*1024) {
        dataSize = roundSize(byteCount/(1024*1024*1024)) + ' GB';
    } else if (byteCount > 1024*1024) {
        dataSize = roundSize(byteCount/(1024*1024)) + ' MB';
    } else if (byteCount > 1024) {
        dataSize = roundSize(byteCount/1024) + ' kB';
    } else {
        dataSize = byteCount + ' B';
    }
    return dataSize;
}

function translateTime(elapsed) {
    let secs = elapsed / 1000.0;

    const one_day = 24.0*60.0*60.0;
    const one_hour = 60.0*60.0;
    const one_minute = 60.0;
    
    const days = Math.floor(secs / one_day);
    secs -= days * one_day;
    const hours = Math.floor(secs / one_hour);
    secs -= hours * one_hour;
    const mins = Math.floor(secs / one_minute);
    secs -= mins * one_minute;

    let start = false;
    let display = '';
    if (days > 0) {
        start = true;
        display += `${days} day`;
        if (days > 1)
            display += 's';
    }
    if (hours > 0 || start) {
        if (start) display += ', ';
        start = true;
        display += `${hours} hr`;
        if (hours !== 1)
            display += 's';
    }
    if (mins > 0 || start) {
        if (start) display += ', ';
        start = true;
        display += `${mins} min`;
        if (mins !== 1)
            display += 's';
    }
    if (start) display += ', ';
    secs = Math.floor( secs * 1000) / 1000;
    display += `${secs} s`;

    return display
}

function assembleSummaryHeader(name) {
    const headerRow = document.createElement("tr");
    const header = document.createElement("th");
    header.setAttribute("colspan", "2");
    header.textContent = name;
    headerRow.appendChild(header);
    return headerRow;
}

function assembleDataHeader(name) {
    const headerRow = document.createElement("tr");
    const header = document.createElement("th");
    header.setAttribute("colspan", "4");
    header.textContent = name;
    headerRow.appendChild(header);
    return headerRow;
}

function assembleDetailHeader() {
    const headerRow = document.createElement('tr');
    const idCol = document.createElement('th');
    idCol.textContent = 'ID';
    const sizeCol = document.createElement('th');
    sizeCol.textContent = 'Size';
    const md5Col = document.createElement('th');
    md5Col.textContent = 'MD5 Checksum';
    const uploadCol = document.createElement('th');
    uploadCol.textContent = 'Upload Count';
    headerRow.appendChild(idCol);
    headerRow.appendChild(sizeCol);
    headerRow.appendChild(md5Col);
    headerRow.appendChild(uploadCol);
    return headerRow;
}

function assembleSummaryRow(name, version) {
    let row = document.createElement("tr");
    let nameEl = document.createElement("td");
    nameEl.textContent = name;
    let versionEl = document.createElement("td");
    versionEl.textContent = version;
    row.appendChild(nameEl);
    row.appendChild(versionEl);
    return row;
}

function assembleDataRow(id, source, time, data) {
    let row = document.createElement('tr');
    let idEl = document.createElement('td');
    idEl.textContent = id;
    let sourceEl = document.createElement('td');
    sourceEl.textContent = source;
    let timeEl = document.createElement('td');
    timeEl.textContent = time;
    let dataEl = document.createElement('td');
    dataEl.textContent = data;
    row.appendChild(idEl);
    row.appendChild(sourceEl);
    row.appendChild(timeEl);
    row.appendChild(dataEl);
    return row;
}

function assembleDetailRow(id, len, md5, url, uploadCount) {
    let row = document.createElement('tr');
    let idEl = document.createElement('td');
    let linkEl = document.createElement('a');
    linkEl.setAttribute('href', '..' + url);
    linkEl.textContent = id;
    idEl.appendChild(linkEl);
    let sizeEl = document.createElement('td');
    sizeEl.textContent = translateSize(len);
    let md5El = document.createElement('td');
    md5El.textContent = md5;
    let uploadEl = document.createElement('td');
    uploadEl.textContent = uploadCount;
    row.appendChild(idEl);
    row.appendChild(sizeEl);
    row.appendChild(md5El);
    row.appendChild(uploadEl);
    return row; 
}

function emptyCurrentData() {
    let row = document.createElement('tr');
    let elem = document.createElement('td');
    elem.setAttribute('colspan', '4');
    elem.textContent = 'No Data Observed';
    row.appendChild(elem);
    return row;
}

function updateStatus(tablePrefix) {
    sendCommand('status').then((data) => {
        const versionsTable = tablePrefix + '-versions';
        const statsTable = tablePrefix + '-stats';
        const n0183Table = tablePrefix + '-nmea0183';
        const n2000Table = tablePrefix + '-nmea2000';
        const detailTable = tablePrefix + '-detail';
    
        let versions = document.getElementById(versionsTable);
        versions.replaceChildren(assembleSummaryHeader("Versions"));
        versions.appendChild(assembleSummaryRow("Firmware", data.version.firmware));
        versions.appendChild(assembleSummaryRow("Command Processor", data.version.commandproc));
        versions.appendChild(assembleSummaryRow("NMEA0183", data.version.nmea0183));
        versions.appendChild(assembleSummaryRow("NMEA2000", data.version.nmea2000));
        versions.appendChild(assembleSummaryRow("IMU", data.version.imu));
        versions.appendChild(assembleSummaryRow("Serialiser", data.version.serialiser));
    
        let totalFileSize = 0;
        for (let n = 0; n < data.files.count; ++n) {
            if ('len' in data.files.detail[n] && isFinite(data.files.detail[n].len)) {
                totalFileSize += data.files.detail[n].len;
            }
        }
    
        let stats = document.getElementById(statsTable);
        stats.replaceChildren(assembleSummaryHeader("Status"));
        stats.appendChild(assembleSummaryRow("Elapsed Time", translateTime(data.elapsed)));
        stats.appendChild(assembleSummaryRow("Webserver Status Current", data.webserver.current));
        stats.appendChild(assembleSummaryRow("Webserver Status Boot", data.webserver.boot));
        stats.appendChild(assembleSummaryRow("Files on Logger", data.files.count));
        stats.appendChild(assembleSummaryRow("Total Size", translateSize(totalFileSize)));
    
        let nmea0183 = document.getElementById(n0183Table);
        if (nmea0183 !== null) {
            nmea0183.replaceChildren(assembleDataHeader("Latest NMEA0183 Data"));
            if (data.data.nmea0183.count === 0) {
                nmea0183.appendChild(emptyCurrentData());
            }
            for (let n = 0; n < data.data.nmea0183.count; ++n) {
                nmea0183.appendChild(assembleDataRow(
                    data.data.nmea0183.detail[n].name,
                    data.data.nmea0183.detail[n].tag,
                    data.data.nmea0183.detail[n].time + ' ' + data.data.nmea0183.detail[n].time_units,
                    data.data.nmea0183.detail[n].display));
            }
        }
        
        let nmea2000 = document.getElementById(n2000Table);
        if (nmea2000 !== null) {
            nmea2000.replaceChildren(assembleDataHeader("Latest NMEA2000 Data"));
            if (data.data.nmea2000.count === 0) {
                nmea2000.appendChild(emptyCurrentData());
            }
            for (let n = 0; n < data.data.nmea2000.count; ++n) {
                nmea2000.appendChild(assembleDataRow(
                    data.data.nmea2000.detail[n].name,
                    data.data.nmea2000.detail[n].tag,
                    data.data.nmea2000.detail[n].time + ' ' + data.data.nmea2000.detail[n].time_units,
                    data.data.nmea2000.detail[n].display));
            }
        }
    
        let detail = document.getElementById(detailTable);
        if (detail !== null) {
            detail.replaceChildren(assembleDetailHeader());
            for (let n = 0; n < data.files.count; ++n) {
                if (data.files.detail[n].hasOwnProperty('id') &&
                    data.files.detail[n].hasOwnProperty('len') &&
                    data.files.detail[n].hasOwnProperty('md5') &&
                    data.files.detail[n].hasOwnProperty('url') &&
                    data.files.detail[n].hasOwnProperty('uploads'))
                    detail.appendChild(
                        assembleDetailRow(
                            data.files.detail[n].id,
                            data.files.detail[n].len,
                            data.files.detail[n].md5,
                            data.files.detail[n].url,
                            data.files.detail[n].uploads
                        )
                    );
            }
        }
    });
}

function redirectCatalog() {
    sendCommand('snapshot catalog').then((data) => {
        let frame = document.getElementById('downloadFrame');
        frame.setAttribute('src', '..' + data.url);
    });
}

function redirectArchive() {
    sendCommand('snapshot archive').then((data) => {
        let frame = document.getElementById('downloadFrame');
        frame.setAttribute('src', '..' + data.url);
    });
}

function updateIndexStatus() {
    const update = () => { updateStatus('index'); }
    after(500, update);
}

function updateStatusData() {
    const update = () => { updateStatus('status'); }
    after(500, update);
}

function saveCatalog() {
    const update = () => { redirectCatalog(); }
    after(500, update);
}

function archiveLogs() {
    const update = () => { redirectArchive(); }
    after(500, update);
}
