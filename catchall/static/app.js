import { microphoneLevel, retrySeconds } from "./caption-presentation.js";
import { buildAudioFrame } from "./audio-protocol.js";
import { CaptionTranscriptState } from "./caption-transcript-state.js";
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
    describeConnectionView,
    describeServerView,
} from "./browser-view-state.js";
import {
    INVALID_SERVER_MESSAGE_NOTICE,
    parseServerMessage,
} from "./server-message.js";
import {
    buildTranscriptDocument,
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

const transcriptState = new CaptionTranscriptState();
const sessionState = new CaptionSessionState();
const audioSupport = detectAudioCaptureSupport(window);

let connection = null;
let serverReady = false;
let serverBusy = false;
let retryTimer = null;
const retryCard = document.querySelector("#retry-card");
const retryCountdown = document.querySelector("#retry-countdown");
const inputLevel = document.querySelector("#input-level");
let lastMeterUpdate = 0;

function stopRetryCountdown() {
    window.clearInterval(retryTimer);
    retryTimer = null;
}


const captureSession = new AudioCaptureSession({
    environment: window,
    support: audioSupport,
    onMessage: handleAudioCaptureMessage,
});

function setConnectionStatus(status) {
    connectionStatus.textContent = status;
}

function applyViewState(view) {
    if (view === null) {
        return;
    }

    if ("serverReady" in view) {
        serverReady = view.serverReady;
    }

    if (view.connectionStatus !== undefined) {
        setConnectionStatus(view.connectionStatus);
    }

    if (view.recordingStatus !== undefined) {
        recordingStatus.textContent = view.recordingStatus;
    }

    if (view.alert !== undefined) {
        captionAlert.textContent = view.alert;
    } else if (view.clearAlert) {
        captionAlert.textContent = "";
    }

    if (view.provisionalCaption !== undefined) {
        provisionalCaption.textContent = view.provisionalCaption;
    }

    if (view.plainLanguageStatus !== undefined) {
        plainLanguageStatus.textContent = view.plainLanguageStatus;
    }

    if (view.microphoneDisabled !== undefined) {
        microphoneButton.disabled = view.microphoneDisabled;
    }

    if (view.plainLanguageDisabled !== undefined) {
        plainLanguageToggle.disabled = view.plainLanguageDisabled;
    }
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
    const hasTranscript = transcriptState.hasCommittedCaptions;

    exportButton.disabled = !hasTranscript;
    clearButton.disabled = !hasTranscript || captureSession.busy;
}

function handleAudioCaptureMessage(event) {
    if (event.data.type === "audio-frame") {
        const samples = new Int16Array(event.data.samples);
        // Limit visual updates to 10Hz; audio frames still pass through unchanged.
        const now = performance.now();
        if (now - lastMeterUpdate >= 100) {
            const level = microphoneLevel(samples);
            inputLevel.style.setProperty("--level", String(level));
            inputLevel.setAttribute("aria-valuenow", String(Math.round(level * 100)));
            lastMeterUpdate = now;
        }
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
    let message;

    try {
        message = parseServerMessage(event.data);
    } catch (error) {
        console.warn("Ignored invalid server message:", error);
        captionAlert.textContent = INVALID_SERVER_MESSAGE_NOTICE;
        return;
    }

    const view = describeServerView(message);
    applyViewState(view);
    if (view?.kind === "server-busy") {
        serverBusy = true;
        retryCard.hidden = false;
        retryCountdown.textContent = "Waiting for a session";
    }

    if (view?.kind === "recognizer-ready") {
        serverBusy = false;
        retryCard.hidden = true;
        stopRetryCountdown();
        connection.markStable();
        setReadyMicrophoneState();

        const restoreMessage = sessionState.recognizerReady();

        if (restoreMessage === null) {
            plainLanguageToggle.disabled = false;
            plainLanguageStatus.textContent = "Off. Plain-language processing runs on the CatchAll server.";
        } else {
            plainLanguageToggle.checked = true;
            plainLanguageToggle.disabled = true;
            plainLanguageStatus.textContent = "Restoring plain-language captions...";
            connection.send(JSON.stringify(restoreMessage));
        }
    }

    if (message.type === "caption" && message.state === "committed") {
        const update = transcriptState.recordCommitted(message);

        if (update.firstCaption) {
            finalizedCaptions.textContent = "";
        }

        const segment = document.createElement("span");
        segment.className = "committed-phrase";
        segment.textContent = `${update.segment.text} `;

        finalizedCaptions.append(segment);

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
            plainLanguageStatus.textContent = "On. Finalized sentences are rewritten on the CatchAll server.";

            if (!transcriptState.hasPlainCaptions) {
                plainLanguageCaptions.textContent = "Waiting for a finalized sentence...";
            }
        } else {
            plainLanguageStatus.textContent = "Off. Plain-language processing runs on the CatchAll server.";
            plainLanguageCaptions.textContent = "Plain-language captions are off.";
            transcriptState.resetPlainDisplay();
        }
    }

    if (message.type === "plain_caption" && sessionState.plainLanguageEnabled) {
        const captionKey = sessionState.plainCaptionKey(message.sentence_id);
        const update = transcriptState.recordPlain(message, captionKey);

        if (update.firstCaption) {
            plainLanguageCaptions.textContent = "";
        }

        const segment = document.createElement("span");
        segment.textContent = `${update.caption.text} `;
        segment.dataset.status = update.caption.status;

        if (update.caption.status === "fallback") {
            segment.title = "The plain-language rewrite was rejected; " + "this is the verbatim sentence.";
        }

        plainLanguageCaptions.append(segment);
    }

    if (view?.kind === "capture-finalized") {
        setReadyMicrophoneState("Microphone stopped");
        updateTranscriptActions();
    }
}

function handleConnectionState(connectionState) {
    stopRetryCountdown();
    if (serverBusy && connectionState.state === "waiting") {
        const deadline = Date.now() + connectionState.delay;
        const tick = () => {
            const remaining = retrySeconds(deadline, Date.now());
            retryCountdown.textContent = remaining ? `Retrying in ${remaining} s` : "Connecting…";
        };
        tick();
        retryTimer = window.setInterval(tick, 250);
    } else if (serverBusy && ["connecting", "reconnecting", "open"].includes(connectionState.state)) {
        retryCountdown.textContent = "Connecting…";
    }
    const view = describeConnectionView(connectionState);
    applyViewState(view);

    if (view?.kind === "connection-waiting") {
        sessionState.disconnect();
        plainLanguageToggle.checked = sessionState.plainLanguageRequested;

        if (captureSession.busy) {
            void stopCapture({
                finalize: false,
                stoppedStatus: "Microphone stopped after connection loss.",
            });
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
    inputLevel.style.setProperty("--level", "0");
    inputLevel.setAttribute("aria-valuenow", "0");

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
        committedSegments: transcriptState.committedSegments,
        plainCaptions: [...transcriptState.plainCaptions.values()],
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

    transcriptState.clear();

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
    stopRetryCountdown();
}, { once: true });
