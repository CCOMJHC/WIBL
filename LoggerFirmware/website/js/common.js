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
