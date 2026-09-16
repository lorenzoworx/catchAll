export function describeServerView(message) {
    if (message.type === "connection" && message.status === "connected") {
        return {
            connectionStatus: "Connected. Preparing speech recognition...",
        };
    }

    if (message.type === "recognizer" && message.status === "loading") {
        return {
            kind: "recognizer-loading",
            recordingStatus: "Loading speech recognition",
            microphoneDisabled: true,
        };
    }

    if (message.type === "recognizer" && message.status === "ready") {
        return {
            kind: "recognizer-ready",
            serverReady: true,
            connectionStatus: "Connected",
            clearAlert: true,
        };
    }

    if (message.type === "error" && message.code === "recognizer_unavailable") {
        return {
            kind: "recognizer-unavailable",
            serverReady: false,
            recordingStatus: "Speech recognition unavailable",
            alert: "Speech recognition could not be started.",
            microphoneDisabled: true,
            plainLanguageDisabled: true,
        };
    }

    if (message.type === "error" && message.code === "recognition_failed") {
        return {
            alert: "Some speech could not be captioned. Listening continues.",
        };
    }

    if (message.type === "error" && message.code === "audio_buffer_full") {
        return {
            alert: "Audio processing fell behind, so some audio was skipped.",
        };
    }

    if (message.type === "capture" && message.status === "finalized") {
        return { kind: "capture-finalized" };
    }

    return null;
}

export function describeConnectionView({ state, delay = 0 }) {
    if (state === "connecting") {
        return { connectionStatus: "Connecting..." };
    }

    if (state === "reconnecting") {
        return { connectionStatus: "Reconnecting..." };
    }

    if (state === "open") {
        return { connectionStatus: "Connected. Waiting for server..." };
    }

    if (state === "error") {
        return { connectionStatus: "Connection error" };
    }

    if (state === "waiting") {
        const seconds = Number.isFinite(delay) && delay >= 0 ? delay / 1000 : 0;

        return {
            kind: "connection-waiting",
            serverReady: false,
            connectionStatus: `Reconnecting in ${seconds} seconds...`,
            recordingStatus: "Microphone unavailable while reconnecting.",
            provisionalCaption: "Connection lost; provisional caption discarded.",
            plainLanguageStatus: "Unavailable while reconnecting.",
            microphoneDisabled: true,
            plainLanguageDisabled: true,
        };
    }

    return null;
}
