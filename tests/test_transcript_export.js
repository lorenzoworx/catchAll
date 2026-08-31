import assert from "node:assert/strict";
import test from "node:test";

import {
    buildTranscriptDocument,
    formatTranscriptText,
    makeTranscriptFilename,
} from "../catchall/static/transcript-export.js";

test("exports only committed verbatim captions", () => {
    const document = buildTranscriptDocument({
        committedSegments: [
            {
                text: "Hello world.",
                startSample: 0,
                endSample: 16000,
            },
            {
                text: "How are you?",
                startSample: 16000,
                endSample: 32000,
            },
        ],
        plainCaptions: [],
        provisionalText: "This must not appear.",
    });

    assert.equal(
        document.verbatim,
        "Hello world. How are you?",
    );
    assert.equal(
        JSON.stringify(document).includes(
            "This must not appear.",
        ),
        false,
    );
});

test("exports only accepted plain alternatives", () => {
    const document = buildTranscriptDocument({
        committedSegments: [],
        plainCaptions: [
            {
                original: "We require assistance.",
                text: "We need help.",
                status: "simplified",
                startSample: 0,
                endSample: 16000,
            },
            {
                original: "The balance is $100.",
                text: "The balance is $100.",
                status: "fallback",
                startSample: 16000,
                endSample: 32000,
            },
            {
                original: "Please wait.",
                text: "Please wait.",
                status: "unchanged",
                startSample: 32000,
                endSample: 48000,
            },
        ],
    });

    assert.deepEqual(
        document.plainLanguageAlternatives,
        [
            {
                original: "We require assistance.",
                text: "We need help.",
                startSeconds: 0,
                endSeconds: 1,
            },
        ],
    );
});

test("formats a readable text transcript", () => {
    const document = buildTranscriptDocument({
        committedSegments: [
            {
                text: "We require assistance.",
                startSample: 0,
                endSample: 16000,
            },
        ],
        plainCaptions: [
            {
                original: "We require assistance.",
                text: "We need help.",
                status: "simplified",
                startSample: 0,
                endSample: 16000,
            },
        ],
    });

    const text = formatTranscriptText(document);

    assert.match(
        text,
        /Verbatim\nWe require assistance\./,
    );
    assert.match(
        text,
        /Original: We require assistance\./,
    );
    assert.match(text, /Plain: We need help\./);
});

test("rejects invalid sample rate", () => {
    assert.throws(
        () =>
            buildTranscriptDocument({
                committedSegments: [],
                plainCaptions: [],
                sampleRate: 0,
            }),
        /sampleRate must be positive/,
    );
});

test("creates deterministic filename", () => {
    const filename = makeTranscriptFilename(
        new Date("2026-08-28T12:30:15.000Z"),
    );

    assert.equal(
        filename,
        "catchall-transcript-"
            + "2026-08-28T12-30-15-000Z.txt",
    );
});