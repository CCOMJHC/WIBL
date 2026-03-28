function generateUUID() {
    // Public Domain/MIT
    let d = new Date().getTime(); //Timestamp
    let d2 = (typeof performance !== "undefined" && performance.now && performance.now() * 1000) || 0; //Time in microseconds since page-load or 0 if unsupported
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        let r = Math.random() * 16; //random number between 0 and 16
        if (d > 0) {
            //Use timestamp until depleted
            r = ((d + r) % 16) | 0;
            d = Math.floor(d / 16);
        } else {
            //Use microseconds since page-load if supported
            r = ((d2 + r) % 16) | 0;
            d2 = Math.floor(d2 / 16);
        }
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
}

function generateUniqueID() {
    const uuid = generateUUID();
    const prefix = document.getElementById("unique-id").value;
    let identifier = "";
    if (prefix.includes("-")) {
        identifier = prefix;
    } else {
        identifier = prefix + "-" + uuid;
    }
    document.getElementById("unique-id").value = identifier;
}

// Use the command processor version reported by the device config.
// This avoids SetConfig/lab defaults rejection when firmware version changes.
let commandProcVersion = "1.4.3";

/** Escape string for use inside a JSON double-quoted value (backslash and quote). */
function escapeJsonString(s) {
    if (s == null) return "";
    return String(s)
        .replace(/\\/g, "\\\\")
        .replace(/"/g, '\\"');
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
    const upload_dropbox_en = document.getElementById("upload-dropbox").checked ? true : false;
    const openWifiConnect_en = document.getElementById("open-wifi-connect").checked ? true : false;
    const wifiMode = document.getElementById("wifimode").value;
    const stationDelay = document.getElementById("retry-delay").value;
    const stationRetries = document.getElementById("retry-count").value;
    const stationTimeout = document.getElementById("join-timeout").value;
    const mdnsName = document.getElementById("mdns-name").value;
    const apSSID = document.getElementById("ap-ssid").value;
    const stationSSID = document.getElementById("station-ssid").value;
    const apPassword = document.getElementById("ap-password").value;
    const stationPassword = document.getElementById("station-password").value;
    const uploadServer = document.getElementById("upload-server").value;
    const uploadPort = document.getElementById("upload-port").value;
    const uploadTimeout = document.getElementById("upload-timeout").value;
    const uploadInterval = document.getElementById("upload-interval").value;
    const uploadDuration = document.getElementById("upload-duration").value;
    const dropboxPath = document.getElementById("upload-dropbox-path").value;
    const port1BaudRate = document.getElementById("port1-baud").value;
    const port2BaudRate = document.getElementById("port2-baud").value;
    const wifiSsid1 = document.getElementById("wifi-ssid1").value;
    const wifiSsid2 = document.getElementById("wifi-ssid2").value;
    const wifiSsid3 = document.getElementById("wifi-ssid3").value;
    const wifiSsid4 = document.getElementById("wifi-ssid4").value;
    const wifiSsid5 = document.getElementById("wifi-ssid5").value;
    const wifiPass1 = document.getElementById("wifi-pass1").value;
    const wifiPass2 = document.getElementById("wifi-pass2").value;
    const wifiPass3 = document.getElementById("wifi-pass3").value;
    const wifiPass4 = document.getElementById("wifi-pass4").value;
    const wifiPass5 = document.getElementById("wifi-pass5").value;
    const ignoredWifiSsid1 = document.getElementById("ignored-wifi-ssid1").value;
    const ignoredWifiSsid2 = document.getElementById("ignored-wifi-ssid2").value;
    const ignoredWifiSsid3 = document.getElementById("ignored-wifi-ssid3").value;
    const ignoredWifiSsid4 = document.getElementById("ignored-wifi-ssid4").value;
    const ignoredWifiSsid5 = document.getElementById("ignored-wifi-ssid5").value;
    let config = `{
        "version": {
            "commandproc": "${escapeJsonString(commandProcVersion)}"
        },
        "uniqueID": "${escapeJsonString(uniqueID)}",
        "shipname": "${escapeJsonString(shipname)}",
        "udpbridge": ${udpbridge},
        "enable": {
            "nmea0183": ${nmea0183_en},
            "nmea2000": ${nmea2000_en},
            "imu": ${imu_en},
            "powermonitor": ${powermon_en},
            "sdmmc": ${sdmmc_en},
            "udpbridge": ${udpbr_en},
            "webserver": ${webserver_en},
            "upload": ${upload_en},
            "uploadDropbox": ${upload_dropbox_en}
        },
        "wifi": {
            "mode": "${escapeJsonString(wifiMode)}",
            "station": {
                "delay": ${stationDelay},
                "retries": ${stationRetries},
                "timeout": ${stationTimeout},
                "mdns": "${escapeJsonString(mdnsName)}"
            },
            "ssids": {
                "ap": "${escapeJsonString(apSSID)}",
                "station": "${escapeJsonString(stationSSID)}"
            },
            "passwords": {
                "ap": "${escapeJsonString(apPassword)}",
                "station": "${escapeJsonString(stationPassword)}"
            },
            "openconnect": ${openWifiConnect_en}
        },
        "baudrate": {
            "port1": ${port1BaudRate},
            "port2": ${port2BaudRate}
        },
        "upload": {
            "server": "${escapeJsonString(uploadServer)}",
            "port": "${escapeJsonString(uploadPort)}",
            "timeout": "${escapeJsonString(uploadTimeout)}",
            "interval": "${escapeJsonString(uploadInterval)}",
            "duration": "${escapeJsonString(uploadDuration)}",
            "dropboxPath": "${escapeJsonString(dropboxPath)}",
            "wifiSsid1": "${escapeJsonString(wifiSsid1)}",
            "wifiSsid2": "${escapeJsonString(wifiSsid2)}",
            "wifiSsid3": "${escapeJsonString(wifiSsid3)}",
            "wifiSsid4": "${escapeJsonString(wifiSsid4)}",
            "wifiSsid5": "${escapeJsonString(wifiSsid5)}",
            "wifiPass1": "${escapeJsonString(wifiPass1)}",
            "wifiPass2": "${escapeJsonString(wifiPass2)}",
            "wifiPass3": "${escapeJsonString(wifiPass3)}",
            "wifiPass4": "${escapeJsonString(wifiPass4)}",
            "wifiPass5": "${escapeJsonString(wifiPass5)}",
            "ignoredWifiSsid1": "${escapeJsonString(ignoredWifiSsid1)}",
            "ignoredWifiSsid2": "${escapeJsonString(ignoredWifiSsid2)}",
            "ignoredWifiSsid3": "${escapeJsonString(ignoredWifiSsid3)}",
            "ignoredWifiSsid4": "${escapeJsonString(ignoredWifiSsid4)}",
            "ignoredWifiSsid5": "${escapeJsonString(ignoredWifiSsid5)}"
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
    if (config.version && typeof config.version.commandproc === "string" && config.version.commandproc.length > 0) {
        commandProcVersion = config.version.commandproc;
    }

    document.getElementById("nmea0183").checked = config.enable.nmea0183;
    document.getElementById("nmea2000").checked = config.enable.nmea2000;
    document.getElementById("imu").checked = config.enable.imu;
    document.getElementById("epower").checked = config.enable.powermonitor;
    document.getElementById("memcontroller").checked = config.enable.sdmmc;
    document.getElementById("nmeabridge").checked = config.enable.udpbridge;
    document.getElementById("webserveronboot").checked = config.enable.webserver;
    document.getElementById("autoupload").checked = config.enable.upload;
    document.getElementById("upload-dropbox").checked = config.enable.uploadDropbox || false;
    document.getElementById("unique-id").value = config.uniqueID;
    document.getElementById("ship-name").value = config.shipname;
    document.getElementById("bridge-port").value = config.udpbridge;
    document.getElementById("wifimode").value = config.wifi.mode;
    document.getElementById("retry-delay").value = config.wifi.station.delay;
    document.getElementById("retry-count").value = config.wifi.station.retries;
    document.getElementById("join-timeout").value = config.wifi.station.timeout;
    document.getElementById("mdns-name").value = config.wifi.station.mdns;
    document.getElementById("ap-ssid").value = config.wifi.ssids.ap;
    document.getElementById("station-ssid").value = config.wifi.ssids.station;
    if (config.wifi.passwords) {
        if (typeof config.wifi.passwords.ap === "string")
            document.getElementById("ap-password").value = config.wifi.passwords.ap;
        if (typeof config.wifi.passwords.station === "string")
            document.getElementById("station-password").value = config.wifi.passwords.station;
    }
    document.getElementById("connected-ssid").value = config.wifi.ssids.station || "";
    document.getElementById("wifi-status").value = config.wifi.status || "";
    document.getElementById("open-wifi-connect").checked = config.wifi.openconnect || false;
    document.getElementById("port1-baud").value = config.baudrate.port1;
    document.getElementById("port2-baud").value = config.baudrate.port2;
    document.getElementById("upload-server").value = config.upload.server;
    document.getElementById("upload-port").value = config.upload.port;
    document.getElementById("upload-timeout").value = config.upload.timeout;
    document.getElementById("upload-interval").value = config.upload.interval;
    document.getElementById("upload-duration").value = config.upload.duration;
    document.getElementById("upload-dropbox-path").value =
        (config.upload && typeof config.upload.dropboxPath === "string") ? config.upload.dropboxPath : "";
    if (config.upload) {
        document.getElementById("wifi-ssid1").value = config.upload.wifiSsid1 || "";
        document.getElementById("wifi-ssid2").value = config.upload.wifiSsid2 || "";
        document.getElementById("wifi-ssid3").value = config.upload.wifiSsid3 || "";
        document.getElementById("wifi-ssid4").value = config.upload.wifiSsid4 || "";
        document.getElementById("wifi-ssid5").value = config.upload.wifiSsid5 || "";
        // For security, preset passwords may be omitted from config; only overwrite if present.
        if (typeof config.upload.wifiPass1 === "string")
            document.getElementById("wifi-pass1").value = config.upload.wifiPass1;
        if (typeof config.upload.wifiPass2 === "string")
            document.getElementById("wifi-pass2").value = config.upload.wifiPass2;
        if (typeof config.upload.wifiPass3 === "string")
            document.getElementById("wifi-pass3").value = config.upload.wifiPass3;
        if (typeof config.upload.wifiPass4 === "string")
            document.getElementById("wifi-pass4").value = config.upload.wifiPass4;
        if (typeof config.upload.wifiPass5 === "string")
            document.getElementById("wifi-pass5").value = config.upload.wifiPass5;
        document.getElementById("ignored-wifi-ssid1").value = config.upload.ignoredWifiSsid1 || "";
        document.getElementById("ignored-wifi-ssid2").value = config.upload.ignoredWifiSsid2 || "";
        document.getElementById("ignored-wifi-ssid3").value = config.upload.ignoredWifiSsid3 || "";
        document.getElementById("ignored-wifi-ssid4").value = config.upload.ignoredWifiSsid4 || "";
        document.getElementById("ignored-wifi-ssid5").value = config.upload.ignoredWifiSsid5 || "";
    }
}

function uploadCurrentConfig() {
    const config = createJSONConfig();
    sendSetupConfig(config).then((data) => {});
}

function uploadDefaultConfig() {
    const config = createJSONConfig();
    sendLabDefaultsConfig(config).then((data) => {});
}

function saveConfigLocally() {
    sendCommand("snapshot config").then((data) => {
        if (data.url === "") {
            window.alert("Failed to generate defaults snapshot on logger");
        } else {
            document.getElementById("downloadFrame").setAttribute("src", ".." + data.url);
        }
    });
}

function saveDefaultLocally() {
    sendCommand("snapshot defaults").then((data) => {
        if (data.url === "") {
            window.alert("Failed to generate defaults snapshot on logger");
        } else {
            document.getElementById("downloadFrame").setAttribute("src", ".." + data.url);
        }
    });
}

function loadConfigLocally() {
    let input = document.createElement("input");
    input.type = "file";
    updateText = function () {
        let reader = new FileReader();
        reader.readAsText(input.files[0]);
        reader.onerror = function () {
            console.log(reader.error);
            window.alert("Failed on read: " + reader.error.message);
        };
        reader.onload = function () {
            try {
                let json = JSON.parse(reader.result);
                parseConfigJSON(json);
            } catch (error) {
                console.log(error);
                window.alert("Failed on load: " + error.message);
            }
        };
    };
    input.onchange = function () {
        updateText();
    };
    input.click();
}

function initWifiSsidSelects() {
    initWifiList("wifi-ssid1");
    initWifiList("wifi-ssid2");
    initWifiList("wifi-ssid3");
    initWifiList("wifi-ssid4");
    initWifiList("wifi-ssid5");
    initWifiList("ignored-wifi-ssid1");
    initWifiList("ignored-wifi-ssid2");
    initWifiList("ignored-wifi-ssid3");
    initWifiList("ignored-wifi-ssid4");
    initWifiList("ignored-wifi-ssid5");
}

function initWifiList(selectId) {
    const availableSSIDs = ["HomeNetwork", "CoffeeShopWiFi", "OfficeWiFi"]; // TODO: scan for actual SSIDs
    const select = document.getElementById(selectId);
    // Clear existing options except the default
    select.querySelectorAll("option:not([value=''])").forEach((opt) => opt.remove());
    // Populate dynamically
    availableSSIDs.forEach((ssid) => {
        const option = document.createElement("option");
        option.value = ssid;
        option.textContent = ssid;
        select.appendChild(option);
    });
}

function bootstrapConfig() {
    const boot = () => {
        sendCommand("setup").then((data) => {
            parseConfigJSON(data);
        });
    };
    after(500, boot);
}
