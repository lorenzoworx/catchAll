import assert from "node:assert/strict";
import test from "node:test";

import {
    describeMicrophoneError,
    detectAudioCaptureSupport,
} from "../catchall/static/audio-capture.js";

function supportedEnvironment() {
    return {
        isSecureContext: true,
        navigator: {
            mediaDevices: {
                getUserMedia() {},
            },
        },
        AudioContext: class AudioContext {},
        AudioWorkletNode: class AudioWorkletNode {},
    };
}

test("returns the browser audio constructors when capture is supported", () => {
    const environment = supportedEnvironment();
    const result = detectAudioCaptureSupport(environment);

    assert.equal(result.supported, true);
    assert.equal(result.AudioContextClass, environment.AudioContext);
    assert.equal(result.AudioWorkletNodeClass, environment.AudioWorkletNode);
});

test("supports the prefixed Safari audio context", () => {
    const environment = supportedEnvironment();
    environment.webkitAudioContext = environment.AudioContext;
    delete environment.AudioContext;

    const result = detectAudioCaptureSupport(environment);

    assert.equal(result.supported, true);
    assert.equal(result.AudioContextClass, environment.webkitAudioContext);
});

test("rejects capture outside a secure context", () => {
    const environment = supportedEnvironment();
    environment.isSecureContext = false;

    assert.deepEqual(detectAudioCaptureSupport(environment), {
        supported: false,
        reason: "Microphone capture requires HTTPS or localhost.",
    });
});

test("reports missing browser audio capabilities", () => {
    const noMicrophone = supportedEnvironment();
    delete noMicrophone.navigator.mediaDevices;
    assert.equal(
        detectAudioCaptureSupport(noMicrophone).reason,
        "This browser does not support microphone capture.",
    );

    const noContext = supportedEnvironment();
    delete noContext.AudioContext;
    assert.equal(
        detectAudioCaptureSupport(noContext).reason,
        "This browser does not support live audio processing.",
    );

    const noWorklet = supportedEnvironment();
    delete noWorklet.AudioWorkletNode;
    assert.equal(
        detectAudioCaptureSupport(noWorklet).reason,
        "This browser does not support audio worklets.",
    );
});

test("describes actionable microphone failures", () => {
    assert.equal(
        describeMicrophoneError({ name: "NotAllowedError" }),
        "Microphone permission was denied. Allow access in your browser and try again.",
    );
    assert.equal(
        describeMicrophoneError({ name: "NotFoundError" }),
        "No microphone was found.",
    );
    assert.match(
        describeMicrophoneError({ name: "NotReadableError" }),
        /another application/,
    );
    assert.equal(
        describeMicrophoneError(new Error("unexpected")),
        "The microphone could not be started.",
    );
});
