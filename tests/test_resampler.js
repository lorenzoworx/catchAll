import assert from "node:assert/strict";
import test from "node:test";

import { StreamingResampler, floatToInt16 } from "../catchall/static/resampler.js";

function concatenate(chunks) {
    const length = chunks.reduce(
        (total, chunk) => total + chunk.length,
        0
    );
    const result = new Float32Array(length);

    let offset = 0;

    for (const chunk of chunks) {
        result.set(chunk,  offset);
        offset += chunk.length;
    }

    return result;
}

function processInChunks(resampler, input, chunkSize) {
    const output = [];

    for (let offset = 0; offset < input.length; offset += chunkSize) {
        output.push(
            resampler.process(
                input.slice(offset, offset + chunkSize)
            )
        );
    }

    return concatenate(output);
}

test("48 kHz input produces 16 kHz output duration", () => {
    const input = new Float32Array(48_000);
    const resampler = new StreamingResampler(48_000, 16_000);

    const output = processInChunks(resampler, input, 128);

    assert.equal(output.length, 16_000);
});

test("44.1 kHz input preserves approximately one second", () => {
    const input = new Float32Array(44_100);
    const resampler = new StreamingResampler(44_100, 16_000);

    const output = processInChunks(resampler, input, 128);

    assert.ok(Math.abs(output.length - 16_000) <= 1);
});

test("constant input remains constant after resampling", () => {
    const input = new Float32Array(4_800);
    input.fill(0.25);

    const resampler = new StreamingResampler(48_000, 16_000);
    const output = processInChunks(resampler, input, 128);

    for (const sample of output) {
        assert.ok(Math.abs(sample - 0.25) < 1e-6);
    }

});

test("chunked processing matches one-shot processing", () => {
    const input = Float32Array.from(
        { length: 4_800 },
        (_, index) => Math.sin(index / 20)
    );

    const oneShot = new StreamingResampler(48_000, 16_000).process(input);

    const chunked = processInChunks(
        new StreamingResampler(48_000, 16_000),
        input,
        128
    );

    assert.equal(chunked.length, oneShot.length);

    for (let index = 0; index < oneShot.length; index += 1) {
        assert.ok(
            Math.abs(chunked[index] - oneShot[index]) < 1e-6
        );
    }
});

test("empty input produces empty output", () => {
    const resampler = new StreamingResampler(48_000, 16_000);

    assert.equal(
        resampler.process(new Float32Array(0)).length,
        0
    );
});

test("float samples convert to signed 16-bit PCM", () => {
    assert.equal(floatToInt16(-1), -32768);
    assert.equal(floatToInt16(-0.5), -16384);
    assert.equal(floatToInt16(0), 0);
    assert.equal(floatToInt16(0.5), 16384);
    assert.equal(floatToInt16(1), 32767);
    assert.equal(floatToInt16(2), 32767);    
});