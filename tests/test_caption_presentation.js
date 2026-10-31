import test from "node:test";
import assert from "node:assert/strict";
import { microphoneLevel, retrySeconds } from "../catchall/static/caption-presentation.js";
test("microphone meter is silent for silence and bounded for loud input", () => {
    assert.equal(microphoneLevel(new Int16Array()), 0);
    assert.equal(microphoneLevel(new Int16Array(320)), 0);
    assert.equal(microphoneLevel(new Int16Array([32767, -32768])), 1);
    assert.ok(microphoneLevel(new Int16Array([1000, -1000])) > 0);
});
test("countdown reflects the scheduled retry without going negative", () => {
    assert.equal(retrySeconds(2500, 1000), 2);
    assert.equal(retrySeconds(2500, 2499), 1);
    assert.equal(retrySeconds(2500, 2500), 0);
    assert.equal(retrySeconds(2500, 9000), 0);
});
