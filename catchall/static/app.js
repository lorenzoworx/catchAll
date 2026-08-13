const connectionStatus = document.querySelector("#connection-status");

function setConnectionStatus(status) {
    connectionStatus.textContent = status;
}

function makeWebSocketUrl() {
    const url = new URL("/ws", window.location.origin);
    url.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

    return url.toString();
}

function connect() {
    setConnectionStatus("Connecting...");

    const socket = new WebSocket(makeWebSocketUrl());

    socket.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);

        if (message.type === "connection" && message.status === "connected") {
            setConnectionStatus("Connected");
        }
    });

    socket.addEventListener("error", () => {
        setConnectionStatus("Connection error");
    });

    socket.addEventListener("close", () => {
        setConnectionStatus("Disconnected");
    });
}

connect();