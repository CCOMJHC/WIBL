function generateUUID() { // Public Domain/MIT
    let d = new Date().getTime();//Timestamp
    let d2 = ((typeof performance !== 'undefined') && performance.now && (performance.now()*1000)) || 0;//Time in microseconds since page-load or 0 if unsupported
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        let r = Math.random() * 16;//random number between 0 and 16
        if(d > 0){//Use timestamp until depleted
            r = (d + r)%16 | 0;
            d = Math.floor(d/16);
        } else {//Use microseconds since page-load if supported
            r = (d2 + r)%16 | 0;
            d2 = Math.floor(d2/16);
        }
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

function generateUniqueID() {
    const uuid = generateUUID();
    const prefix = document.getElementById("unique-id").value;
    let identifier = '';
    if (prefix.includes('-')) {
        identifier = prefix;
    } else {
        identifier = prefix + '-' + uuid;
    }
    document.getElementById("unique-id").value = identifier;
}

function createJSONConfig() {
    const uniqueID = document.getElementById("unique-id").value;
    const shipname = document.getElementById("ship-name").value;
    const udpbridge = document.getElementById("bridge-port").value;
    const nmea0183_en = document.getElementById("nmea0183").checked ? true : false;
    const nmea2000_en = document.getElementById("nmea2000").checked ? true : false;
    const imu_en = document.getElementById("imu").checked ? true : false;
    const powermon_en = document.getElementById("epower").checked ? true : false;
    const sdmmc_en = document.getElementById("memcontroller").checked ? true : false;
    const udpbr_en = document.getElementById("nmeabridge").checked ? true : false;
    const webserver_en = document.getElementById("webserveronboot").checked ? true : false;
    const upload_en = document.getElementById("autoupload").checked ? true : false;
    const wifiMode = document.getElementById("wifimode").value;
    const stationDelay = document.getElementById("retry-delay").value;
    const stationRetries = document.getElementById("retry-count").value;
    const stationTimeout = document.getElementById("join-timeout").value;
    const apSSID = document.getElementById("ap-ssid").value;
    const stationSSID = document.getElementById("station-ssid").value;
    const apPassword = document.getElementById("ap-password").value;
    const stationPassword = document.getElementById("station-password").value;
    const uploadServer = document.getElementById("upload-server").value;
    const uploadPort = document.getElementById("upload-port").value;
    const uploadTimeout = document.getElementById("upload-timeout").value;
    const uploadInterval = document.getElementById("upload-interval").value;
    const uploadDuration = document.getElementById("upload-duration").value;
    const port1BaudRate = document.getElementById("port1-baud").value;
    const port2BaudRate = document.getElementById("port2-baud").value;
    let config = `{
        "version": {
            "commandproc": "1.4.0"
        },
        "uniqueID": "${uniqueID}",
        "shipname": "${shipname}",
        "udpbridge": ${udpbridge},
        "enable": {
            "nmea0183": ${nmea0183_en},
            "nmea2000": ${nmea2000_en},
            "imu": ${imu_en},
            "powermonitor": ${powermon_en},
            "sdmmc": ${sdmmc_en},
            "udpbridge": ${udpbr_en},
            "webserver": ${webserver_en},
            "upload": ${upload_en}
        },
        "wifi": {
            "mode": "${wifiMode}",
            "station": {
                "delay": ${stationDelay},
                "retries": ${stationRetries},
                "timeout": ${stationTimeout}
            },
            "ssids": {
                "ap": "${apSSID}",
                "station": "${stationSSID}"
            },
            "passwords": {
                "ap": "${apPassword}",
                "station": "${stationPassword}"
            }
        },
        "baudrate": {
            "port1": ${port1BaudRate},
            "port2": ${port2BaudRate}
        },
        "upload": {
            "server": "${uploadServer}",
            "port": ${uploadPort},
            "timeout": ${uploadTimeout},
            "interval": ${uploadInterval},
            "duration": ${uploadDuration}
        }
    }`;
    let data = JSON.parse(config);
    return JSON.stringify(data);
}

function parseConfigJSON(config) {
    /* Checking the enable components first will cause the parse to fail if the JSON isn't
     * in the right format, and therefore avoid the system resetting other components in
     * the configuration and over-writing correct values.
     */
    document.getElementById("nmea0183").checked = config.enable.nmea0183;
    document.getElementById("nmea2000").checked = config.enable.nmea2000;
    document.getElementById("imu").checked = config.enable.imu;
    document.getElementById("epower").checked = config.enable.powermonitor;
    document.getElementById("memcontroller").checked = config.enable.sdmmc;
    document.getElementById("nmeabridge").checked = config.enable.udpbridge;
    document.getElementById("webserveronboot").checked = config.enable.webserver;
    document.getElementById("autoupload").value = config.enable.upload;
    
    document.getElementById("unique-id").value = config.uniqueID;
    document.getElementById("ship-name").value = config.shipname;

    document.getElementById("bridge-port").value = config.udpbridge;
    
    document.getElementById("wifimode").value = config.wifi.mode;
    document.getElementById("retry-delay").value = config.wifi.station.delay;
    document.getElementById("retry-count").value = config.wifi.station.retries;
    document.getElementById("join-timeout").value = config.wifi.station.timeout;
    document.getElementById("ap-ssid").value = config.wifi.ssids.ap;
    document.getElementById("station-ssid").value = config.wifi.ssids.station;
    document.getElementById("ap-password").value = config.wifi.passwords.ap;
    document.getElementById("station-password").value = config.wifi.passwords.station;

    document.getElementById("port1-baud").value = config.baudrate.port1;
    document.getElementById("port2-baud").value = config.baudrate.port2;

    document.getElementById("upload-server").value = config.upload.server;
    document.getElementById("upload-port").value = config.upload.port;
    document.getElementById("upload-timeout").value = config.upload.timeout;
    document.getElementById("upload-interval").value = config.upload.interval;
    document.getElementById("upload-duration").value = config.upload.duration;
}

function uploadCurrentConfig() {
    const config = createJSONConfig();
    sendCommand('setup ' + config).then((data) => {});
}

function uploadDefaultConfig() {
    const config = createJSONConfig();
    sendCommand('lab defaults ' + config).then((data) => {});
}

function saveConfigLocally() {
    sendCommand('snapshot config').then((data) => {
        if (data.url === "") {
            window.alert("Failed to generate defaults snapshot on logger");
        } else {
            document.getElementById('downloadFrame').setAttribute('src', '..' + data.url);
        }
    });
}

function saveDefaultLocally() {
    sendCommand('snapshot defaults').then((data) => {
        if (data.url === "") {
            window.alert("Failed to generate defaults snapshot on logger");
        } else {
            document.getElementById('downloadFrame').setAttribute('src', '..' + data.url);
        }
    });
}

function loadConfigLocally() {
    let input = document.createElement('input');
    input.type = 'file';
    updateText = function() {
        let reader = new FileReader();
        reader.readAsText(input.files[0]);
        reader.onerror = function() {
            console.log(reader.error);
            window.alert('Failed on read: ' + reader.error.message);
        }
        reader.onload = function() {
            try {
                json = JSON.parse(reader.result);
                parseConfigJSON(json);
            } catch (error) {
                console.log(error);
                window.alert('Failed on load: ' + error.message);
            }
        }
    }
    input.onchange = function() {
        updateText();
    }
    input.click();
}

function bootstrapConfig() {
    const boot = () => {
        sendCommand('setup').then((data) => {
            parseConfigJSON(data);
        });
    }
    after(500, boot);
}
