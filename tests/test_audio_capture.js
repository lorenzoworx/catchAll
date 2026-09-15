import assert from "node:assert/strict";
import test from "node:test";

import {
    AudioCaptureSession,
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

function sessionEnvironment({ failWorklet = false } = {}) {
    const calls = [];
    const track = {
        stop() {
            calls.push("track.stop");
        },
    };
    const stream = {
        getTracks() {
            return [track];
        },
    };
    const mediaSource = {
        connect(node) {
            calls.push(["source.connect", node]);
        },
        disconnect() {
            calls.push("source.disconnect");
        },
    };

    class FakeAudioContext {
        constructor(options) {
            calls.push(["context.create", options]);
            this.state = "suspended";
            this.audioWorklet = {
                async addModule(url) {
                    calls.push(["worklet.addModule", url]);

                    if (failWorklet) {
                        throw new Error("worklet failed");
                    }
                },
            };
        }

        createMediaStreamSource(receivedStream) {
            calls.push(["source.create", receivedStream]);
            return mediaSource;
        }

        async resume() {
            calls.push("context.resume");
            this.state = "running";
        }

        async close() {
            calls.push("context.close");
            this.state = "closed";
        }
    }

    class FakeAudioWorkletNode {
        constructor(context, name, options) {
            calls.push(["node.create", context, name, options]);
            this.listener = null;
            this.port = {
                addEventListener: (type, listener) => {
                    calls.push(["port.addEventListener", type]);
                    this.listener = listener;
                },
                start: () => calls.push("port.start"),
            };
        }

        disconnect() {
            calls.push("node.disconnect");
        }
    }

    const environment = {
        isSecureContext: true,
        navigator: {
            mediaDevices: {
                async getUserMedia(constraints) {
                    calls.push(["getUserMedia", constraints]);
                    return stream;
                },
            },
        },
        AudioContext: FakeAudioContext,
        AudioWorkletNode: FakeAudioWorkletNode,
    };

    return { calls, environment, mediaSource, stream, track };
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

test("starts a browser capture session and forwards worklet messages", async () => {
    const { calls, environment } = sessionEnvironment();
    const messages = [];
    const session = new AudioCaptureSession({
        environment,
        onMessage: messages.push.bind(messages),
    });

    await session.start();

    assert.equal(session.active, true);
    assert.deepEqual(calls[0], [
        "getUserMedia",
        {
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            },
            video: false,
        },
    ]);
    assert.deepEqual(calls[2], [
        "worklet.addModule",
        "/static/capture-worklet.js",
    ]);
    assert.equal(calls.includes("port.start"), true);
    assert.equal(calls.includes("context.resume"), true);

    const event = { data: { type: "ready" } };
    session.captureNode.listener(event);
    assert.deepEqual(messages, [event]);
});

test("stops every capture resource and can be called repeatedly", async () => {
    const { calls, environment } = sessionEnvironment();
    const session = new AudioCaptureSession({ environment });

    await session.start();
    await session.stop();
    await session.stop();

    assert.equal(session.active, false);
    assert.equal(calls.filter((call) => call === "node.disconnect").length, 1);
    assert.equal(calls.filter((call) => call === "source.disconnect").length, 1);
    assert.equal(calls.filter((call) => call === "track.stop").length, 1);
    assert.equal(calls.filter((call) => call === "context.close").length, 1);
});

test("cleans up an acquired stream when worklet startup fails", async () => {
    const { calls, environment } = sessionEnvironment({ failWorklet: true });
    const session = new AudioCaptureSession({ environment });

    await assert.rejects(session.start(), /worklet failed/);

    assert.equal(session.active, false);
    assert.equal(calls.includes("track.stop"), true);
    assert.equal(calls.includes("context.close"), true);
});

test("leaves no active session when microphone permission is denied", async () => {
    const { environment } = sessionEnvironment();
    const denial = new Error("denied");
    denial.name = "NotAllowedError";
    environment.navigator.mediaDevices.getUserMedia = async () => {
        throw denial;
    };
    const session = new AudioCaptureSession({ environment });

    await assert.rejects(session.start(), (error) => error === denial);

    assert.equal(session.active, false);
    assert.equal(describeMicrophoneError(denial).includes("permission"), true);
});

test("cancels capture while microphone permission is still pending", async () => {
    const { calls, environment, stream } = sessionEnvironment();
    let grantPermission;
    environment.navigator.mediaDevices.getUserMedia = () => new Promise((resolve) => {
        grantPermission = () => resolve(stream);
    });
    const session = new AudioCaptureSession({ environment });

    const startPromise = session.start();
    assert.equal(session.starting, true);

    await session.stop();
    grantPermission();

    assert.equal(await startPromise, false);
    assert.equal(session.busy, false);
    assert.equal(calls.filter((call) => call === "track.stop").length, 1);
    assert.equal(
        calls.some((call) => Array.isArray(call) && call[0] === "context.create"),
        false,
    );
});
