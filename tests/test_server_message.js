import assert from "node:assert/strict";
import test from "node:test";

import {
    INVALID_SERVER_MESSAGE_NOTICE,
    parseServerMessage,
    ServerMessageError,
} from "../catchall/static/server-message.js";

test("provides the user-facing invalid-message notice", () => {
    assert.equal(
        INVALID_SERVER_MESSAGE_NOTICE,
        "A server update was invalid and was ignored. Captioning can continue.",
    );
});

test("parses the server events used by the caption interface", () => {
    const messages = [
        { type: "connection", status: "connected" },
        { type: "recognizer", status: "loading" },
        { type: "recognizer", status: "ready" },
        { type: "error", code: "recognition_failed" },
        {
            type: "caption",
            state: "committed",
            text: "Final text.",
            start_sample: 0,
            end_sample: 16000,
        },
        {
            type: "caption",
            state: "provisional",
            text: "",
            window_start_sample: 0,
            window_end_sample: 16000,
        },
        { type: "plain_language", enabled: true },
        {
            type: "plain_caption",
            sentence_id: "sentence-0-16000",
            original: "We require assistance.",
            text: "We need help.",
            status: "simplified",
            start_sample: 0,
            end_sample: 16000,
        },
        { type: "capture", status: "finalized" },
    ];

    for (const message of messages) {
        assert.deepEqual(parseServerMessage(JSON.stringify(message)), message);
    }
});

test("allows unknown typed events for forward compatibility", () => {
    const message = { type: "future_event", value: 1 };

    assert.deepEqual(parseServerMessage(JSON.stringify(message)), message);
});

test("rejects malformed envelopes", () => {
    const invalidMessages = [
        [new Uint8Array(), /must be text/],
        ["{", /not valid JSON/],
        ["null", /JSON object/],
        ["[]", /JSON object/],
        ["{}", /type must be a non-empty string/],
    ];

    for (const [data, expected] of invalidMessages) {
        assert.throws(
            () => parseServerMessage(data),
            (error) => error instanceof ServerMessageError && expected.test(error.message),
        );
    }
});

test("rejects malformed known events", () => {
    const invalidMessages = [
        { type: "recognizer", status: "finished" },
        { type: "error", code: "" },
        { type: "caption", state: "committed", text: "Missing samples." },
        {
            type: "caption",
            state: "provisional",
            text: 42,
            window_start_sample: 0,
            window_end_sample: 16000,
        },
        { type: "plain_language", enabled: "yes" },
        {
            type: "plain_caption",
            sentence_id: "sentence-0-16000",
            original: "Original.",
            text: "Plain.",
            status: "unsafe",
            start_sample: 0,
            end_sample: 16000,
        },
        { type: "capture", status: "pending" },
    ];

    for (const message of invalidMessages) {
        assert.throws(
            () => parseServerMessage(JSON.stringify(message)),
            ServerMessageError,
        );
    }
});
