class SocketManager {
    // The websocket
    sock;
    // Event handlers
    event_handlers;
    // Event types
    event_types = [
        "list-wibl-files"
    ];

    constructor(url) {
        this.sock = new WebSocket(url);
        // Setup empty event handler list for each event type
        this.event_handlers = {};
        for (const etype of this.event_types) {
            this.event_handlers[etype] = [];
        }
        // Register SocketManager handleEvent function with the socket. This will handle all events from
        // the socket and deliver to registered event listeners.
        this.sock.addEventListener("message", (event) => this.handleEvent(event));
    }

    addHandler(event_type, handler_fn) {
        if (!(event_type in this.event_handlers)) {
            console.error(`Unknown event type ${event_type}`);
            return false;
        }
        this.event_handlers[event_type].push(handler_fn);
        return true;
    }

    handleEvent(event) {
        console.log("In handleEvent()...");
        const data = JSON.parse(event.data);
        if (!("event" in data)) {
            console.error(`No event type in event ${data}`);
            return false;
        }
        if (!(data.event in this.event_handlers)) {
            console.error(`Unable to handle unknown event type ${data.event} in event ${data}`);
            return false;
        }
        // Deliver event to all interested handlers
        for (const handler_fn of this.event_handlers[data.event]) {
            handler_fn(data);
        }
    }

    _doSendRequest(event_type) {
        setTimeout(() => {
            if (this.sock.readyState === 1) {
                console.log(`Socket is ready, sending event type ${event_type}`);
                this.sock.send(JSON.stringify({type: event_type}));
            } else {
                // Socket isn't ready...
                console.log("Socket isn't ready, waiting...");
                this._doSendRequest(event_type);
            }
        }, 20);

    }

    sendRequest(event_type) {
        // TODO: Support sending requests with payloads
        if (this.event_types.indexOf(event_type) === -1) {
            console.error(`Unable to sendRequest for unknown event type ${event_type}.`);
            return
        }
        this._doSendRequest(event_type);
    }
}
