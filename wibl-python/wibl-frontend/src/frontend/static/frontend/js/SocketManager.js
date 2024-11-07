class SocketManager {
    // The websocket
    sock;
    // Socket type, one of: "wibl",
    type;
    // Event handlers
    event_handlers;
    // Event types
    event_types = {
        "wibl": [
            "list-wibl-files",
            "list-wibl-details"
        ]
    };
    // Class object to track singleton instances by URL
    static _instances = {};

    constructor(url, type) {
        // TODO: Verify type is valid.
        SocketManager._instances[url] = this;
        this.type = type;
        this.sock = new WebSocket(url);
        // Setup empty event handler list for each event type
        this.event_handlers = {};
        for (const etype of this.event_types[this.type]) {
            this.event_handlers[etype] = [];
        }
        // Register SocketManager handleEvent function with the socket. This will handle all events from
        // the socket and deliver to registered event listeners.
        this.sock.addEventListener("message", (event) => this.handleEvent(event));
    }

    static getInstance(url, type) {
        if (url in SocketManager._instances) {
            // TODO: Verify type matching that of instance.
            return SocketManager._instances[url];
        } else {
            return new SocketManager(url, type);
        }
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

    _doSendRequest(event_type, fileid = "") {
        setTimeout(() => {
            if (this.sock.readyState === 1) {
                console.log(`Socket is ready, sending event type ${event_type}`);
                if (event_type === "list-wibl-details") {
                    this.sock.send(JSON.stringify({type: event_type, file_id: fileid})) ;
                } else {
                    this.sock.send(JSON.stringify({type: event_type}));
                }
            } else {
                // Socket isn't ready...
                console.log("Socket isn't ready, waiting...");
                this._doSendRequest(event_type, fileid);
            }
        }, 20);

    }

    sendRequest(event_type, fileid = "") {
        // TODO: Support sending requests with payloads
        if (this.event_types[this.type].indexOf(event_type) === -1) {
            console.error(`Unable to sendRequest for unknown event type ${event_type}.`);
            return
        }
        if (event_type === "list-wibl-details" && fileid === "") {
            console.error("Unable to sendRequest to list details, missing parameter 'file-id'. ");
            return
        }
        this._doSendRequest(event_type, fileid);
    }
}
