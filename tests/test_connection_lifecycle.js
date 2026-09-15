import assert from "node:assert/strict";
import test from "node:test";

import {
    CaptionSessionState,
    ReconnectingSocket,
} from "../catchall/static/connection-lifecycle.js";

class FakeSocket {
    constructor(url) {
        this.url = url;
        this.readyState = 0;
        this.listeners = new Map();
        this.sent = [];
        this.closed = false;
    }

    addEventListener(type, listener) {
        const listeners = this.listeners.get(type) ?? [];
        listeners.push(listener);
        this.listeners.set(type, listeners);
    }

    emit(type, event = {}) {
        if (type === "open") {
            this.readyState = 1;
        } else if (type === "close") {
            this.readyState = 3;
        }

        for (const listener of this.listeners.get(type) ?? []) {
            listener(event);
        }
    }

    send(message) {
        this.sent.push(message);
    }

    close() {
        this.closed = true;
        this.emit("close");
    }
}

function makeHarness() {
    const sockets = [];
    const scheduled = [];
    const states = [];
    const messages = [];
    const lifecycle = new ReconnectingSocket({
        url: "ws://example.test/ws",
        socketFactory: (url) => {
            const socket = new FakeSocket(url);
            sockets.push(socket);
            return socket;
        },
        schedule: (callback, delay) => {
            const timer = { callback, delay, cancelled: false };
            scheduled.push(timer);
            return timer;
        },
        cancelSchedule: (timer) => {
            timer.cancelled = true;
        },
        retryDelays: [100, 200],
        onMessage: (event) => messages.push(event.data),
        onStateChange: (state) => states.push(state),
    });

    return { lifecycle, messages, scheduled, sockets, states };
}

test("connects and forwards messages from the active socket", () => {
    const { lifecycle, messages, sockets, states } = makeHarness();

    lifecycle.start();
    sockets[0].emit("open");
    sockets[0].emit("message", { data: "caption" });

    assert.equal(sockets[0].url, "ws://example.test/ws");
    assert.deepEqual(messages, ["caption"]);
    assert.deepEqual(states, [
        { state: "connecting" },
        { state: "open" },
    ]);
});

test("reconnects with bounded backoff after a close", () => {
    const { lifecycle, scheduled, sockets, states } = makeHarness();

    lifecycle.start();
    sockets[0].emit("close");
    assert.equal(scheduled[0].delay, 100);

    scheduled[0].callback();
    assert.deepEqual(states.at(-1), { state: "reconnecting" });
    sockets[1].emit("close");
    assert.equal(scheduled[1].delay, 200);

    scheduled[1].callback();
    sockets[2].emit("close");
    assert.equal(scheduled[2].delay, 200);
    assert.deepEqual(states.at(-1), { state: "waiting", delay: 200 });
});

test("a stable connection resets the reconnect delay", () => {
    const { lifecycle, scheduled, sockets } = makeHarness();

    lifecycle.start();
    sockets[0].emit("close");
    scheduled[0].callback();
    sockets[1].emit("open");
    lifecycle.markStable();
    sockets[1].emit("close");

    assert.equal(scheduled[1].delay, 100);
});

test("sends only while the active socket is open", () => {
    const { lifecycle, sockets } = makeHarness();

    lifecycle.start();
    assert.equal(lifecycle.send("early"), false);

    sockets[0].emit("open");
    assert.equal(lifecycle.send("ready"), true);
    assert.deepEqual(sockets[0].sent, ["ready"]);
});

test("stopping cancels a pending reconnect", () => {
    const { lifecycle, scheduled, sockets } = makeHarness();

    lifecycle.start();
    sockets[0].emit("close");
    lifecycle.stop();

    assert.equal(scheduled[0].cancelled, true);
    scheduled[0].callback();
    assert.equal(sockets.length, 1);
});

test("invokes browser timer functions without a socket-manager receiver", () => {
    const sockets = [];
    let scheduleReceiver = "not called";
    let cancelReceiver = "not called";
    const timer = {};
    const lifecycle = new ReconnectingSocket({
        url: "ws://example.test/ws",
        socketFactory: (url) => {
            const socket = new FakeSocket(url);
            sockets.push(socket);
            return socket;
        },
        schedule: function () {
            scheduleReceiver = this;
            return timer;
        },
        cancelSchedule: function () {
            cancelReceiver = this;
        },
    });

    lifecycle.start();
    sockets[0].emit("close");
    lifecycle.stop();

    assert.equal(scheduleReceiver, undefined);
    assert.equal(cancelReceiver, undefined);
});

test("plain-language preference survives a new server session", () => {
    const state = new CaptionSessionState();

    state.requestPlainLanguage(true);
    state.confirmPlainLanguage(true);
    state.disconnect();

    assert.equal(state.plainLanguageRequested, true);
    assert.equal(state.plainLanguageEnabled, false);
    assert.deepEqual(state.recognizerReady(), {
        type: "plain_language",
        enabled: true,
    });
});

test("plain caption keys are scoped to the server session", () => {
    const state = new CaptionSessionState();

    state.recognizerReady();
    const first = state.plainCaptionKey("sentence-0-100");
    state.disconnect();
    state.recognizerReady();
    const second = state.plainCaptionKey("sentence-0-100");

    assert.notEqual(first, second);
});
