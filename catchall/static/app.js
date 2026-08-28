import { buildAudioFrame } from "./audio-protocol.js";

const connectionStatus = document.querySelector("#connection-status");

const microphoneButton = document.querySelector("#microphone-button");
const recordingStatus = document.querySelector("#recording-status");
const captureDetails = document.querySelector("#capture-details");
const provisionalCaption = document.querySelector("#provisional-caption");
const finalizedCaptions = document.querySelector("#finalized-captions");
const plainLanguageToggle = document.querySelector("#plain-language-toggle");
const plainLanguageStatus = document.querySelector("#plain-language-status");
const plainLanguageCaptions = document.querySelector("#plain-language-captions");

let audioContext = null;
let mediaStream = null;
let mediaSource = null;
let captureNode = null;
let socket = null;
let hasCommittedCaptions = false;
let plainLanguageEnabled = false;
let hasPlainLanguageCaptions = false;

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

    socket = new WebSocket(makeWebSocketUrl());
    // window.catchallSocket = socket;

    socket.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);

        if (message.type === "connection" && message.status === "connected") {
            setConnectionStatus("Connected");
        }

        if (message.type === "recognizer" && message.status == "loading") {
            recordingStatus.textContent = "Loading speech recognition";
            microphoneButton.disabled = true;
        }

        if (message.type === "recognizer" && message.status == "ready") {
            recordingStatus.textContent = "Microphone ready";
            microphoneButton.disabled = false;
            plainLanguageToggle.disabled = false;
            plainLanguageStatus.textContent = "Off. Plain-language processing is local."
        }

        if (message.type === "error" && message.code === "recognizer_unavailable") {
            recordingStatus.textContent = "Speech recognition unavailable";
            microphoneButton.disabled =true;
            plainLanguageToggle.checked = false;
            plainLanguageToggle.disabled = true;
        } 

        if (message.type === "caption" && message.state === "committed") {
            if (!hasCommittedCaptions) {
                finalizedCaptions.textContent = "";
                hasCommittedCaptions = true;
            }

            const segment = document.createElement("span");
            segment.textContent = `${message.text} `;

            finalizedCaptions.append(segment);
        }

        if (message.type === "caption" && message.state === "provisional") {
            provisionalCaption.textContent = message.text;
        }

        if (message.type === "plain_language") {
            plainLanguageEnabled = message.enabled;
            plainLanguageToggle.checked = message.enabled;
            plainLanguageToggle.disabled = false;

            if (plainLanguageEnabled) {
                plainLanguageStatus.textContent = "On. Finalized sentences are rewritten locally.";

                if(!hasPlainLanguageCaptions) {
                    plainLanguageCaptions.textContent = "Waiting for a finalized sentence...";
                }
            } else {
                plainLanguageStatus.textContent = "Off. Plain-language processing is local.";
                plainLanguageCaptions.textContent = "Plain-language captions are off.";
                hasPlainLanguageCaptions = false;
            }

        }

        if (message.type === "plain_caption" && plainLanguageEnabled) {
            if (!hasPlainLanguageCaptions) {
                plainLanguageCaptions.textContent = "";
                hasPlainLanguageCaptions = true;
            }

            const segment = document.createElement("span");
            segment.textContent = `${message.text} `;
            segment.dataset.status = message.status;

            if (message.status === "fallback") {
                segment.title = "The plain-language rewrite was rejected; " + "this is the verbatim sentence.";
            }

            plainLanguageCaptions.append(segment);
        }

    });

    socket.addEventListener("error", () => {
        setConnectionStatus("Connection error");
    });

    socket.addEventListener("close", () => {
        setConnectionStatus("Disconnected");
        socket = null;
        microphoneButton.disabled = true;
        plainLanguageEnabled = false;
        plainLanguageToggle.checked = false;
        plainLanguageToggle.disabled = true;
        plainLanguageStatus.textContent = "Unavailable while disconnected.";
        plainLanguageCaptions.textContent = "Plain-language captions are off.";
        hasPlainLanguageCaptions = false;
    });
}

plainLanguageToggle.addEventListener("change", () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        plainLanguageToggle.checked = plainLanguageEnabled;
        return
    }

    plainLanguageToggle.disabled = true;

    socket.send(JSON.stringify({
        type: "plain_language",
        enabled: plainLanguageToggle.checked,
    }));
});

connect();

async function startCapture() {
    provisionalCaption.textContent = "Listening for speech";
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
            if(event.data.type === "audio-frame") {
                if(socket?.readyState !== WebSocket.OPEN) {
                    return;
                }

                const samples = new Int16Array(event.data.samples);
                const frame = buildAudioFrame(
                    samples,
                    event.data.firstSampleIndex
                );

                socket.send(frame);
                return;
            }

            if (event.data.type === "ready") {
                captureDetails.textContent = 
                    `Input: ${event.data.inputSampleRate} Hz; ` +
                    `prepared output: ${event.data.outputSampleRate} Hz`;
            }

            if (event.data.type === "progress") {
                const seconds = event.data.framedSamples / event.data.outputSampleRate;

                captureDetails.textContent = 
                    `Prepared ${seconds.toFixed(1)} seconds ` +
                    `of 16 kHz audio`;
            }
        });

        captureNode.port.start();
        mediaSource.connect(captureNode);
        await audioContext.resume();

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