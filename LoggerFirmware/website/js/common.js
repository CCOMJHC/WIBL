async function sendCommand(cmdstr, timeout = 10) {
    const base_url = 'http://' + location.host;
    const deadline = Date.now() + timeout * 1000; // timeout is in seconds, scale to ms

    const data = new FormData();
    data.append("command", cmdstr);
    let response = await fetch(base_url + '/command', {
            method: 'POST',
            body: data
        });
    if (response.status !== 202) {
        throw new Error('Command rejected: HTTP ' + response.status);
    }
    const { id } = await response.json();

    let delay = 50; // Delay before retrying, with exponential backoff
    while (Date.now() < deadline) {
        await new Promise(resolve => setTimeout(resolve, delay));
        delay = Math.min(delay * 1.5, 500);

        response = await fetch(base_url + '/results?id=' + id, { cache: 'no-store' });
        if (response.status === 200) return response.json();
        if (response.status !== 202) {
            throw new Error('Result lookup failed: HTTP ' + response.status);
        }
    }
    throw new Error('Command timed out: ' + cmdstr);
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
