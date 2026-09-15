import { buildAudioFrame } from "./audio-protocol.js";
import {
    CaptionSessionState,
    ReconnectingSocket,
} from "./connection-lifecycle.js";
import {
    buildTranscriptDocument,
    formatTranscriptText,
    makeTranscriptFilename,
} from "./transcript-export.js";

const connectionStatus = document.querySelector("#connection-status");

const microphoneButton = document.querySelector("#microphone-button");
const recordingStatus = document.querySelector("#recording-status");
const captureDetails = document.querySelector("#capture-details");
const provisionalCaption = document.querySelector("#provisional-caption");
const finalizedCaptions = document.querySelector("#finalized-captions");
const plainLanguageToggle = document.querySelector("#plain-language-toggle");
const plainLanguageStatus = document.querySelector("#plain-language-status");
const plainLanguageCaptions = document.querySelector("#plain-language-captions");
const exportButton = document.querySelector("#export-button");
const exportStatus = document.querySelector("#export-status");

const committedTranscriptSegments = [];
const plainTranscriptCaptions = new Map();
const sessionState = new CaptionSessionState();

let audioContext = null;
let mediaStream = null;
let mediaSource = null;
let captureNode = null;
let connection = null;
let serverReady = false;
let hasCommittedCaptions = false;
let hasPlainLanguageCaptions = false;

function setConnectionStatus(status) {
    connectionStatus.textContent = status;
}

function makeWebSocketUrl() {
    const url = new URL("/ws", window.location.origin);
    url.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

    return url.toString();
}

function handleSocketMessage(event) {
    const message = JSON.parse(event.data);

    if (message.type === "connection" && message.status === "connected") {
        setConnectionStatus("Connected. Preparing speech recognition...");
    }

    if (message.type === "recognizer" && message.status === "loading") {
        recordingStatus.textContent = "Loading speech recognition";
        microphoneButton.disabled = true;
    }

    if (message.type === "recognizer" && message.status === "ready") {
        serverReady = true;
        connection.markStable();
        setConnectionStatus("Connected");
        recordingStatus.textContent = "Microphone ready";
        microphoneButton.disabled = false;

        const restoreMessage = sessionState.recognizerReady();

        if (restoreMessage === null) {
            plainLanguageToggle.disabled = false;
            plainLanguageStatus.textContent = "Off. Plain-language processing is local.";
        } else {
            plainLanguageToggle.checked = true;
            plainLanguageToggle.disabled = true;
            plainLanguageStatus.textContent = "Restoring plain-language captions...";
            connection.send(JSON.stringify(restoreMessage));
        }
    }

    if (message.type === "error" && message.code === "recognizer_unavailable") {
        serverReady = false;
        recordingStatus.textContent = "Speech recognition unavailable";
        microphoneButton.disabled = true;
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
        committedTranscriptSegments.push({
            text: message.text,
            startSample: message.start_sample,
            endSample: message.end_sample,
        });

        exportButton.disabled = false;
    }

    if (message.type === "caption" && message.state === "provisional") {
        provisionalCaption.textContent = message.text;
    }

    if (message.type === "plain_language") {
        sessionState.confirmPlainLanguage(message.enabled);
        plainLanguageToggle.checked = message.enabled;
        plainLanguageToggle.disabled = false;

        if (sessionState.plainLanguageEnabled) {
            plainLanguageStatus.textContent = "On. Finalized sentences are rewritten locally.";

            if (!hasPlainLanguageCaptions) {
                plainLanguageCaptions.textContent = "Waiting for a finalized sentence...";
            }
        } else {
            plainLanguageStatus.textContent = "Off. Plain-language processing is local.";
            plainLanguageCaptions.textContent = "Plain-language captions are off.";
            hasPlainLanguageCaptions = false;
        }
    }

    if (message.type === "plain_caption" && sessionState.plainLanguageEnabled) {
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

        const captionKey = sessionState.plainCaptionKey(message.sentence_id);

        if (message.status === "simplified") {
            plainTranscriptCaptions.set(
                captionKey,
                {
                    original: message.original,
                    text: message.text,
                    status: message.status,
                    startSample: message.start_sample,
                    endSample: message.end_sample,
                }
            );
        } else {
            plainTranscriptCaptions.delete(captionKey);
        }
    }

    if (message.type === "capture" && message.status === "finalized") {
        recordingStatus.textContent = "Microphone stopped";
        microphoneButton.disabled = false;
    }
}

function handleConnectionState({ state, delay = 0 }) {
    if (state === "connecting") {
        setConnectionStatus("Connecting...");
        return;
    }

    if (state === "reconnecting") {
        setConnectionStatus("Reconnecting...");
        return;
    }

    if (state === "open") {
        setConnectionStatus("Connected. Waiting for server...");
        return;
    }

    if (state === "error") {
        setConnectionStatus("Connection error");
        return;
    }

    if (state === "waiting") {
        serverReady = false;
        sessionState.disconnect();
        setConnectionStatus(`Reconnecting in ${delay / 1000} seconds...`);
        microphoneButton.disabled = true;
        plainLanguageToggle.checked = sessionState.plainLanguageRequested;
        plainLanguageToggle.disabled = true;
        plainLanguageStatus.textContent = "Unavailable while reconnecting.";
        provisionalCaption.textContent = "Connection lost; provisional caption discarded.";

        if (mediaStream !== null || audioContext !== null) {
            void stopCapture({
                finalize: false,
                stoppedStatus: "Microphone stopped after connection loss.",
            });
        } else {
            recordingStatus.textContent = "Microphone unavailable while reconnecting.";
        }
    }
}

plainLanguageToggle.addEventListener("change", () => {
    if (!connection.isOpen || !serverReady) {
        plainLanguageToggle.checked = sessionState.plainLanguageRequested;
        return;
    }

    sessionState.requestPlainLanguage(plainLanguageToggle.checked);
    plainLanguageToggle.disabled = true;

    connection.send(JSON.stringify({
        type: "plain_language",
        enabled: plainLanguageToggle.checked,
    }));
});

async function startCapture() {
    if (!connection.isOpen || !serverReady) {
        recordingStatus.textContent = "Microphone unavailable while reconnecting.";
        return;
    }

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
            if (event.data.type === "audio-frame") {
                const samples = new Int16Array(event.data.samples);
                const frame = buildAudioFrame(
                    samples,
                    event.data.firstSampleIndex
                );

                connection.send(frame);
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
        await stopCapture({ finalize: false });
        recordingStatus.textContent = "Microphone unavailable";
    } finally {
        microphoneButton.disabled = !serverReady;
    }
}

async function stopCapture({
    finalize = true,
    stoppedStatus = "Microphone stopped",
} = {}) {
    microphoneButton.disabled = true;
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

    if (finalize && connection.isOpen && serverReady) {
        recordingStatus.textContent = "Finalizing last phrase...";
        connection.send(JSON.stringify({ type: "capture_end" }));
    } else {
        recordingStatus.textContent = serverReady ? "Microphone ready" : stoppedStatus;
        microphoneButton.disabled = !serverReady;
    }
}

async function toggleCapture() {
    if (mediaStream) {
        await stopCapture();
    } else {
        await startCapture();
    }
}

microphoneButton.addEventListener("click", toggleCapture);

exportButton.addEventListener("click", () => {
    const transcript = buildTranscriptDocument({
        committedSegments: committedTranscriptSegments,
        plainCaptions: [...plainTranscriptCaptions.values()],
    });

    const contents = formatTranscriptText(transcript);
    const blob = new Blob(
        [contents],
        {
            type: "text/plain;charset=utf-8",
        },
    );
    const url = URL.createObjectURL(blob);
    const downloadLink = document.createElement("a");
    downloadLink.href = url;
    downloadLink.download = makeTranscriptFilename();
    document.body.append(downloadLink);
    downloadLink.click();
    downloadLink.remove();
    URL.revokeObjectURL(url);

    exportStatus.textContent = `Exported ${transcript.finalizedSegments.length} finalized segments.`;
});

connection = new ReconnectingSocket({
    url: makeWebSocketUrl(),
    onMessage: handleSocketMessage,
    onStateChange: handleConnectionState,
});
connection.start();

window.addEventListener("pagehide", () => connection.stop(), { once: true });
