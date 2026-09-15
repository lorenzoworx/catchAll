const OPEN_STATE = 1;

export class CaptionSessionState {
    constructor() {
        this.plainLanguageRequested = false;
        this.plainLanguageEnabled = false;
        this.sessionNumber = 0;
    }

    requestPlainLanguage(enabled) {
        this.plainLanguageRequested = enabled;
    }

    disconnect() {
        this.plainLanguageEnabled = false;
    }

    recognizerReady() {
        this.sessionNumber += 1;

        if (!this.plainLanguageRequested) {
            return null;
        }

        return {
            type: "plain_language",
            enabled: true,
        };
    }

    confirmPlainLanguage(enabled) {
        this.plainLanguageRequested = enabled;
        this.plainLanguageEnabled = enabled;
    }

    plainCaptionKey(sentenceId) {
        return `${this.sessionNumber}:${sentenceId}`;
    }
}

export class ReconnectingSocket {
    constructor({
        url,
        socketFactory,
        schedule = (callback, delay) => setTimeout(callback, delay),
        cancelSchedule = (timer) => clearTimeout(timer),
        retryDelays = [500, 1_000, 2_000, 5_000],
        onMessage = () => {},
        onStateChange = () => {},
    }) {
        if (!Array.isArray(retryDelays) || retryDelays.length === 0) {
            throw new RangeError("At least one reconnect delay is required");
        }

        if (retryDelays.some((delay) => !Number.isFinite(delay) || delay < 0)) {
            throw new RangeError("Reconnect delays must be non-negative numbers");
        }

        this.url = url;
        this.socketFactory = socketFactory ?? ((target) => new WebSocket(target));
        this.schedule = schedule;
        this.cancelSchedule = cancelSchedule;
        this.retryDelays = retryDelays;
        this.onMessage = onMessage;
        this.onStateChange = onStateChange;

        this.socket = null;
        this.retryTimer = null;
        this.retryIndex = 0;
        this.hasConnected = false;
        this.stopped = true;
    }

    get isOpen() {
        return this.socket?.readyState === OPEN_STATE;
    }

    start() {
        if (!this.stopped) {
            return;
        }

        this.stopped = false;
        this.connect();
    }

    stop() {
        this.stopped = true;

        if (this.retryTimer !== null) {
            const cancelSchedule = this.cancelSchedule;
            cancelSchedule(this.retryTimer);
            this.retryTimer = null;
        }

        const activeSocket = this.socket;
        this.socket = null;
        activeSocket?.close();
        this.onStateChange({ state: "stopped" });
    }

    send(message) {
        if (!this.isOpen) {
            return false;
        }

        this.socket.send(message);
        return true;
    }

    markStable() {
        this.retryIndex = 0;
    }

    connect() {
        if (this.stopped || this.socket !== null || this.retryTimer !== null) {
            return;
        }

        this.onStateChange({
            state: (this.hasConnected || this.retryIndex > 0)
                ? "reconnecting"
                : "connecting",
        });

        const socket = this.socketFactory(this.url);
        this.socket = socket;

        socket.addEventListener("open", () => {
            if (this.socket !== socket || this.stopped) {
                return;
            }

            this.hasConnected = true;
            this.onStateChange({ state: "open" });
        });

        socket.addEventListener("message", (event) => {
            if (this.socket === socket && !this.stopped) {
                this.onMessage(event);
            }
        });

        socket.addEventListener("error", () => {
            if (this.socket === socket && !this.stopped) {
                this.onStateChange({ state: "error" });
            }
        });

        socket.addEventListener("close", () => {
            if (this.socket !== socket) {
                return;
            }

            this.socket = null;

            if (this.stopped) {
                return;
            }

            const delay = this.retryDelays[
                Math.min(this.retryIndex, this.retryDelays.length - 1)
            ];
            this.retryIndex += 1;
            this.onStateChange({ state: "waiting", delay });
            const schedule = this.schedule;
            this.retryTimer = schedule(() => {
                this.retryTimer = null;
                this.connect();
            }, delay);
        });
    }
}
