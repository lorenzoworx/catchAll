import assert from "node:assert/strict";
import test from "node:test";

import {
    AUDIO_FRAME_TYPE,
    AUDIO_HEADER_BYTES,
    buildAudioFrame,
} from "../catchall/static/audio-protocol.js";


test("builds the binary audio fame header and payload", () => {
    const samples = Int16Array.from([
        -32768,
        -1,
        0,
        1,
        32767,
    ]);

    const frame = buildAudioFrame(samples, 640);
    const view = new DataView(frame);

    assert.equal(
        frame.byteLength,
        AUDIO_HEADER_BYTES + samples.length * 2
    );
    assert.equal(view.getUint8(0), AUDIO_FRAME_TYPE);
    assert.equal(view.getUint8(1), 0);
    assert.equal(view.getUint16(2, true), samples.length);
    assert.equal(view.getBigUint64(4, true), 640n);

    for (let index = 0; index < samples.length; index += 1) {
        assert.equal(
            view.getInt16(
                AUDIO_HEADER_BYTES + index * 2,
                true
            ),
            samples[index]
        );
    }
});

test("preserves sample indexes larger than 32 bits", () => {
    const firstSampleIndex = 2 ** 32 + 320;
    const frame = buildAudioFrame(
        Int16Array.from([0]),
        firstSampleIndex
    );
    const view = new DataView(frame);

    assert.equal(
        view.getBigUint64(4, true),
        BigInt(firstSampleIndex)
    );
});

test("rejects the wrong sample representation", () => {
    assert.throws(
        () => buildAudioFrame(new Float32Array([0]), 0),
        TypeError
    );
});

test("rejects empty audio frames", () => {
    assert.throws(
        () => buildAudioFrame(new Int16Array(0), 0),
        RangeError
    );
});

test("rejects invalid first sample indexes", () => {
    const samples = Int16Array.from([0]);

    assert.throws(
        () => buildAudioFrame(samples, -1),
        RangeError
    );
    assert.throws(
        () => buildAudioFrame(
            samples,
            Number.MAX_SAFE_INTEGER + 1
        ),
        RangeError
    );
});