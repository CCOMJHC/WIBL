class SocketManager {
    // The URL (so that we can create a new socket if need be)
    url;
    // The websocket
    sock;
    // Socket type, one of: "wibl", "geojson"
    type;
    // Event handlers
    event_handlers;
    // Event types
    event_types = {
        "wibl": [
            "list-wibl-files",
            "list-wibl-details",
            "delete-wibl-files"
        ],
        "geojson": [
            "list-geojson-files",
            "list-geojson-details",
            "delete-geojson-files"
        ]
    };
    // Class object to track singleton instances by URL
    static _instances = {};

    constructor(url, type) {
        SocketManager._instances[url] = this;
        this.type = type;
        this.url = url;
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

    reconnect() {
        console.log("In reconnect()...")
        if (this.sock.readyState > 1) {
            console.log("In reconnect(): calling new WebSocket()")
            this.sock = new WebSocket(this.url)
            // Re-register SocketManager handleEvent function with the new socket. This will handle all events from
            // the socket and deliver to registered event listeners.
            this.sock.addEventListener("message", (event) => this.handleEvent(event));
            console.log("In reconnect(): FINISHED calling new WebSocket()")
        }
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
        console.log(`In handleEvent(), event: ${event.toString()}...`);
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

    _doSendRequest(args) {
        setTimeout(() => {
            if (this.sock.readyState === 1) {
                console.log(`Socket is ready, sending event type ${args["type"]} with payload ${args["payload"]}...`);
                this.sock.send(JSON.stringify(args));
            } else if (this.sock.readyState > 1) {
                // Socket isn't ready...
                console.log(`Socket is closed or closing (readyState=${this.sock.readyState}), reconnecting...`);
                this.reconnect();
                this._doSendRequest(args);
            } else {
                // Socket isn't ready...
                console.log(`Socket isn't ready (readyState=${this.sock.readyState}), waiting...`);
                this._doSendRequest(args);
            }
        }, 20);
    }

    sendRequest(event_type, payload) {
        // TODO: Support sending requests with payloads
        if (this.event_types[this.type].indexOf(event_type) === -1) {
            console.error(`Unable to sendRequest for unknown event type ${event_type}.`);
            return
        }
        if (payload == null) {
            payload = {};
        }

        const type = {"type" : event_type};
        const args = {...type, "payload": payload};

        this._doSendRequest(args);
    }
}
