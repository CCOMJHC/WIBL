async function sendCommand(cmdstr, timeout = 10) {
    const url = 'http://' + location.host + '/command';
    let data = new FormData();
    data.append("command", cmdstr);
    let response = await fetch(url, {
            method: 'POST',
            body: data
        });
    return response.json();
}

/** POST config JSON to /setup as raw body so long payloads (e.g. with passwords) are not truncated. */
async function sendSetupConfig(configJson, timeout = 10) {
    const url = 'http://' + location.host + '/setup';
    let response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: configJson
    });
    return response.json();
}

/** POST lab-defaults JSON to /labdefaults as raw body (same truncation benefits as /setup). */
async function sendLabDefaultsConfig(configJson, timeout = 10) {
    const url = 'http://' + location.host + '/labdefaults';
    let response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: configJson
    });
    return response.json();
}

function rebootLogger() {
    let command = 'restart';
    sendCommand(command, 3);
}

function after(delay, callable) {
    const sleep = (delay) => new Promise((resolve) => setTimeout(resolve, delay));
    const pause = async () => {
        await sleep(delay);
        callable();
    }
    pause();
}
