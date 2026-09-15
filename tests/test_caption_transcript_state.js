import assert from "node:assert/strict";
import test from "node:test";

import { CaptionTranscriptState } from "../catchall/static/caption-transcript-state.js";

test("records committed captions in append-only order", () => {
    const state = new CaptionTranscriptState();

    const first = state.recordCommitted({
        text: "First phrase.",
        start_sample: 0,
        end_sample: 16000,
    });
    const second = state.recordCommitted({
        text: "Second phrase.",
        start_sample: 16000,
        end_sample: 32000,
    });

    assert.equal(first.firstCaption, true);
    assert.equal(second.firstCaption, false);
    assert.equal(state.hasCommittedCaptions, true);
    assert.deepEqual(state.committedSegments, [
        {
            text: "First phrase.",
            startSample: 0,
            endSample: 16000,
        },
        {
            text: "Second phrase.",
            startSample: 16000,
            endSample: 32000,
        },
    ]);
});

test("keeps only simplified plain-language alternatives for export", () => {
    const state = new CaptionTranscriptState();

    const simplified = state.recordPlain(
        {
            original: "We require assistance.",
            text: "We need help.",
            status: "simplified",
            start_sample: 0,
            end_sample: 16000,
        },
        "session-1:sentence-1",
    );
    const fallback = state.recordPlain(
        {
            original: "The balance is $100.",
            text: "The balance is $100.",
            status: "fallback",
            start_sample: 16000,
            end_sample: 32000,
        },
        "session-1:sentence-2",
    );

    assert.equal(simplified.firstCaption, true);
    assert.equal(fallback.firstCaption, false);
    assert.deepEqual([...state.plainCaptions.entries()], [
        [
            "session-1:sentence-1",
            {
                original: "We require assistance.",
                text: "We need help.",
                status: "simplified",
                startSample: 0,
                endSample: 16000,
            },
        ],
    ]);
});

test("a fallback replaces an earlier simplified alternative with the same key", () => {
    const state = new CaptionTranscriptState();
    const captionKey = "session-1:sentence-1";

    state.recordPlain(
        {
            original: "We require assistance.",
            text: "We need help.",
            status: "simplified",
            start_sample: 0,
            end_sample: 16000,
        },
        captionKey,
    );
    state.recordPlain(
        {
            original: "We require assistance.",
            text: "We require assistance.",
            status: "fallback",
            start_sample: 0,
            end_sample: 16000,
        },
        captionKey,
    );

    assert.equal(state.plainCaptions.has(captionKey), false);
});

test("resets plain display state without discarding exportable alternatives", () => {
    const state = new CaptionTranscriptState();

    state.recordPlain(
        {
            original: "We require assistance.",
            text: "We need help.",
            status: "simplified",
            start_sample: 0,
            end_sample: 16000,
        },
        "session-1:sentence-1",
    );
    state.resetPlainDisplay();

    assert.equal(state.hasPlainCaptions, false);
    assert.equal(state.plainCaptions.size, 1);
});

test("clears all transcript and display state", () => {
    const state = new CaptionTranscriptState();

    state.recordCommitted({
        text: "First phrase.",
        start_sample: 0,
        end_sample: 16000,
    });
    state.recordPlain(
        {
            original: "We require assistance.",
            text: "We need help.",
            status: "simplified",
            start_sample: 0,
            end_sample: 16000,
        },
        "session-1:sentence-1",
    );

    state.clear();

    assert.equal(state.hasCommittedCaptions, false);
    assert.equal(state.hasPlainCaptions, false);
    assert.deepEqual(state.committedSegments, []);
    assert.equal(state.plainCaptions.size, 0);
});
