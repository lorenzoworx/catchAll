import { buildAudioFrame } from "./audio-protocol.js";
import {
    AudioCaptureSession,
    describeMicrophoneError,
    detectAudioCaptureSupport,
} from "./audio-capture.js";
import {
    CaptionSessionState,
    ReconnectingSocket,
} from "./connection-lifecycle.js";
import {
    buildTranscriptDocument,
    clearTranscriptData,
    formatTranscriptText,
    makeTranscriptFilename,
} from "./transcript-export.js";

const connectionStatus = document.querySelector("#connection-status");

const microphoneButton = document.querySelector("#microphone-button");
const recordingStatus = document.querySelector("#recording-status");
const captureDetails = document.querySelector("#capture-details");
const captionAlert = document.querySelector("#caption-alert");
const provisionalCaption = document.querySelector("#provisional-caption");
const finalizedCaptions = document.querySelector("#finalized-captions");
const plainLanguageToggle = document.querySelector("#plain-language-toggle");
const plainLanguageStatus = document.querySelector("#plain-language-status");
const plainLanguageCaptions = document.querySelector("#plain-language-captions");
const exportButton = document.querySelector("#export-button");
const exportStatus = document.querySelector("#export-status");
const clearButton = document.querySelector("#clear-button");
const clearDialog = document.querySelector("#clear-dialog");
const transcriptStatus = document.querySelector("#transcript-status");

const committedTranscriptSegments = [];
const plainTranscriptCaptions = new Map();
const sessionState = new CaptionSessionState();
const audioSupport = detectAudioCaptureSupport(window);

let connection = null;
let serverReady = false;
let hasCommittedCaptions = false;
let hasPlainLanguageCaptions = false;

const captureSession = new AudioCaptureSession({
    environment: window,
    support: audioSupport,
    onMessage: handleAudioCaptureMessage,
});

function setConnectionStatus(status) {
    connectionStatus.textContent = status;
}

function microphoneCanStart() {
    return serverReady && audioSupport.supported;
}

function setReadyMicrophoneState(status = "Microphone ready") {
    if (!serverReady) {
        microphoneButton.disabled = true;
        return;
    }

    if (!audioSupport.supported) {
        recordingStatus.textContent = audioSupport.reason;
        microphoneButton.disabled = true;
        return;
    }

    recordingStatus.textContent = status;
    microphoneButton.disabled = false;
}

function updateTranscriptActions() {
    const hasTranscript = committedTranscriptSegments.length > 0;

    exportButton.disabled = !hasTranscript;
    clearButton.disabled = !hasTranscript || captureSession.busy;
}

function handleAudioCaptureMessage(event) {
    if (event.data.type === "audio-frame") {
        const samples = new Int16Array(event.data.samples);
        const frame = buildAudioFrame(
            samples,
            event.data.firstSampleIndex,
        );

        connection.send(frame);
        return;
    }

    if (event.data.type === "ready") {
        captureDetails.textContent =
            `Input: ${event.data.inputSampleRate} Hz; `
            + `prepared output: ${event.data.outputSampleRate} Hz`;
    }

    if (event.data.type === "progress") {
        const seconds = event.data.framedSamples / event.data.outputSampleRate;

        captureDetails.textContent =
            `Prepared ${seconds.toFixed(1)} seconds `
            + "of 16 kHz audio";
    }
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
        captionAlert.textContent = "";
        connection.markStable();
        setConnectionStatus("Connected");
        setReadyMicrophoneState();

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
        captionAlert.textContent = "Speech recognition could not be started.";
        microphoneButton.disabled = true;
        plainLanguageToggle.disabled = true;
    }

    if (message.type === "error" && message.code === "recognition_failed") {
        captionAlert.textContent =
            "Some speech could not be captioned. Listening continues.";
    }

    if (message.type === "error" && message.code === "audio_buffer_full") {
        captionAlert.textContent =
            "Audio processing fell behind, so some audio was skipped.";
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

        transcriptStatus.textContent = "";
        updateTranscriptActions();
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
        setReadyMicrophoneState("Microphone stopped");
        updateTranscriptActions();
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

        if (captureSession.busy) {
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

    if (!audioSupport.supported) {
        recordingStatus.textContent = audioSupport.reason;
        microphoneButton.disabled = true;
        return;
    }

    microphoneButton.disabled = true;
    clearButton.disabled = true;
    captionAlert.textContent = "";
    recordingStatus.textContent = "Requesting microphone permission...";

    try {
        const started = await captureSession.start();

        if (!started) {
            return;
        }

        provisionalCaption.textContent = "Listening for speech";
        recordingStatus.textContent = "Microphone recording";
        microphoneButton.textContent = "Stop microphone";
    } catch (error) {
        console.error("Could not start microphone capture:", error);
        await stopCapture({ finalize: false });
        recordingStatus.textContent = describeMicrophoneError(error);
    } finally {
        microphoneButton.disabled = !microphoneCanStart();
        updateTranscriptActions();
    }
}

async function stopCapture({
    finalize = true,
    stoppedStatus = "Microphone stopped",
} = {}) {
    microphoneButton.disabled = true;
    await captureSession.stop();

    microphoneButton.textContent = "Start microphone";
    captureDetails.textContent = "";

    if (finalize && connection.isOpen && serverReady) {
        recordingStatus.textContent = "Finalizing last phrase...";
        connection.send(JSON.stringify({ type: "capture_end" }));
    } else {
        if (serverReady) {
            setReadyMicrophoneState();
            updateTranscriptActions();
        } else {
            recordingStatus.textContent = stoppedStatus;
            microphoneButton.disabled = true;
        }
    }
}

async function toggleCapture() {
    if (captureSession.active) {
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

clearButton.addEventListener("click", () => {
    clearDialog.returnValue = "";
    clearDialog.showModal();
});

clearDialog.addEventListener("close", () => {
    if (clearDialog.returnValue !== "clear") {
        return;
    }

    clearTranscriptData({
        committedSegments: committedTranscriptSegments,
        plainCaptions: plainTranscriptCaptions,
    });
    hasCommittedCaptions = false;
    hasPlainLanguageCaptions = false;

    finalizedCaptions.textContent = "Finalized captions will appear here.";
    provisionalCaption.textContent = "Start the microphone to begin.";
    plainLanguageCaptions.textContent = sessionState.plainLanguageEnabled
        ? "Waiting for a finalized sentence..."
        : "Plain-language captions are off.";
    exportStatus.textContent = "";
    transcriptStatus.textContent = "Transcript cleared.";
    updateTranscriptActions();
});

connection = new ReconnectingSocket({
    url: makeWebSocketUrl(),
    onMessage: handleSocketMessage,
    onStateChange: handleConnectionState,
});
connection.start();

window.addEventListener("pagehide", () => {
    void stopCapture({ finalize: false });
    connection.stop();
}, { once: true });
