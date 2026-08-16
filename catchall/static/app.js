const connectionStatus = document.querySelector("#connection-status");

const microphoneButton = document.querySelector("#microphone-button");
const recordingStatus = document.querySelector("#recording-status")
const captureDetails = document.querySelector("#capture-details");

let audioContext = null;
let mediaStream = null;
let mediaSource = null;
let captureNode = null;

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

async function startCapture() {
    microphoneButton.disabled = true;
    recordingStatus.textContent = "Requesting microphone permission...";

    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            },
            video: false,
        });

        audioContext = new AudioContext({
            latencyHint: "interactive",
        });

        await audioContext.audioWorklet.addModule(
            "/static/capture-worklet.js"
        );

        mediaSource = audioContext.createMediaStreamSource(mediaStream);

        captureNode = new AudioWorkletNode(
            audioContext,
            "capture",
            {
                numberOfInputs: 1,
                numberOfOutputs: 0,
                channelCount: 1,
            }
        );

        captureNode.port.addEventListener("message", (event) => {
            if (event.data.type === "ready") {
                captureDetails.textContent = `Browser sample rate: ${event.data.sampleRate} Hz`;
            }

            if (event.data.type === "progress") {
                const seconds = event.data.totalSamples / event.data.sampleRate;

                captureDetails.textContent = `Captured ${seconds.toFixed(1)} seconds at ` + `${event.data.sampleRate} Hz`;
            }
        });

        captureNode.port.start();
        mediaSource.connect(captureNode);

        recordingStatus.textContent = "Microphone recording";
        microphoneButton.textContent = "Stop microphone";
    } catch (error) {
        console.error("Could not start microphone capture:", error);
        await stopCapture();
        recordingStatus.textContent = "Microphone unavailable";
    } finally {
        microphoneButton.disabled = false;
    }
}

async function stopCapture() {
    captureNode?.disconnect();
    mediaSource?.disconnect();

    for (const track of mediaStream?.getTracks() ?? []) {
        track.stop();
    }

    if (audioContext && audioContext.state !== "closed") {
        await audioContext.close();
    }

    captureNode = null;
    mediaSource = null;
    mediaStream = null;
    audioContext = null;

    microphoneButton.textContent = "Start microphone";
    captureDetails.textContent = "";
    recordingStatus.textContent = "Microphone stopped" ;
}

async function toggleCapture() {
    if (mediaStream) {
        await stopCapture();
    } else {
        await startCapture();
    }
}

microphoneButton.addEventListener("click", toggleCapture);