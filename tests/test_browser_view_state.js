import assert from "node:assert/strict";
import test from "node:test";

import {
    describeConnectionView,
    describeServerView,
} from "../catchall/static/browser-view-state.js";

test("describes initial connection and capture completion states", () => {
    assert.deepEqual(
        describeServerView({ type: "connection", status: "connected" }),
        {
            connectionStatus: "Connected. Preparing speech recognition...",
        },
    );
    assert.deepEqual(
        describeServerView({ type: "capture", status: "finalized" }),
        { kind: "capture-finalized" },
    );
});

test("describes recognizer loading and ready states", () => {
    assert.deepEqual(
        describeServerView({ type: "recognizer", status: "loading" }),
        {
            kind: "recognizer-loading",
            recordingStatus: "Loading speech recognition",
            microphoneDisabled: true,
        },
    );
    assert.deepEqual(
        describeServerView({ type: "recognizer", status: "ready" }),
        {
            kind: "recognizer-ready",
            serverReady: true,
            connectionStatus: "Connected",
            clearAlert: true,
        },
    );
});

test("describes actionable recognizer and processing errors", () => {
    assert.deepEqual(
        describeServerView({
            type: "error",
            code: "recognizer_unavailable",
        }),
        {
            kind: "recognizer-unavailable",
            serverReady: false,
            recordingStatus: "Speech recognition unavailable",
            alert: "Speech recognition could not be started.",
            microphoneDisabled: true,
            plainLanguageDisabled: true,
        },
    );
    assert.deepEqual(
        describeServerView({ type: "error", code: "recognition_failed" }),
        {
            alert: "Some speech could not be captioned. Listening continues.",
        },
    );
    assert.deepEqual(
        describeServerView({ type: "error", code: "audio_buffer_full" }),
        {
            alert: "Audio processing fell behind, so some audio was skipped.",
        },
    );
});

test("describes connection lifecycle states", () => {
    assert.deepEqual(describeConnectionView({ state: "connecting" }), {
        connectionStatus: "Connecting...",
    });
    assert.deepEqual(describeConnectionView({ state: "reconnecting" }), {
        connectionStatus: "Reconnecting...",
    });
    assert.deepEqual(describeConnectionView({ state: "open" }), {
        connectionStatus: "Connected. Waiting for server...",
    });
    assert.deepEqual(describeConnectionView({ state: "error" }), {
        connectionStatus: "Connection error",
    });
});

test("describes the reconnect waiting state", () => {
    assert.deepEqual(
        describeConnectionView({ state: "waiting", delay: 2000 }),
        {
            kind: "connection-waiting",
            serverReady: false,
            connectionStatus: "Reconnecting in 2 seconds...",
            recordingStatus: "Microphone unavailable while reconnecting.",
            provisionalCaption: "Connection lost; provisional caption discarded.",
            plainLanguageStatus: "Unavailable while reconnecting.",
            microphoneDisabled: true,
            plainLanguageDisabled: true,
        },
    );
});

test("ignores messages and connection states without a view transition", () => {
    assert.equal(describeServerView({ type: "future_event" }), null);
    assert.equal(describeConnectionView({ state: "stopped" }), null);
});
