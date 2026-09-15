export function detectAudioCaptureSupport(environment) {
    if (environment.isSecureContext === false) {
        return {
            supported: false,
            reason: "Microphone capture requires HTTPS or localhost.",
        };
    }

    if (typeof environment.navigator?.mediaDevices?.getUserMedia !== "function") {
        return {
            supported: false,
            reason: "This browser does not support microphone capture.",
        };
    }

    const AudioContextClass = environment.AudioContext ?? environment.webkitAudioContext;

    if (typeof AudioContextClass !== "function") {
        return {
            supported: false,
            reason: "This browser does not support live audio processing.",
        };
    }

    if (typeof environment.AudioWorkletNode !== "function") {
        return {
            supported: false,
            reason: "This browser does not support audio worklets.",
        };
    }

    return {
        supported: true,
        AudioContextClass,
        AudioWorkletNodeClass: environment.AudioWorkletNode,
    };
}

export function describeMicrophoneError(error) {
    switch (error?.name) {
        case "NotAllowedError":
            return "Microphone permission was denied. Allow access in your browser and try again.";
        case "NotFoundError":
            return "No microphone was found.";
        case "NotReadableError":
        case "AbortError":
            return "The microphone could not be started. It may be in use by another application.";
        case "SecurityError":
            return "Microphone access is blocked on this page.";
        case "OverconstrainedError":
            return "The available microphone does not support the requested audio settings.";
        default:
            return "The microphone could not be started.";
    }
}

export class AudioCaptureSession {
    constructor({
        environment,
        support = detectAudioCaptureSupport(environment),
        onMessage = () => {},
        workletUrl = "/static/capture-worklet.js",
    }) {
        this.environment = environment;
        this.support = support;
        this.onMessage = onMessage;
        this.workletUrl = workletUrl;

        this.audioContext = null;
        this.mediaStream = null;
        this.mediaSource = null;
        this.captureNode = null;
        this.startToken = null;
    }

    get active() {
        return this.mediaStream !== null;
    }

    get starting() {
        return this.startToken !== null;
    }

    get busy() {
        return this.active || this.starting;
    }

    async start() {
        if (this.busy) {
            return this.active;
        }

        if (!this.support.supported) {
            throw new Error(this.support.reason);
        }

        const startToken = {};
        this.startToken = startToken;

        try {
            const mediaStream = await this.environment.navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                },
                video: false,
            });

            if (this.startToken !== startToken) {
                for (const track of mediaStream.getTracks()) {
                    track.stop();
                }

                return false;
            }

            this.mediaStream = mediaStream;
            this.audioContext = new this.support.AudioContextClass({
                latencyHint: "interactive",
            });

            await this.audioContext.audioWorklet.addModule(this.workletUrl);

            if (this.startToken !== startToken) {
                return false;
            }

            this.mediaSource = this.audioContext.createMediaStreamSource(
                this.mediaStream,
            );
            this.captureNode = new this.support.AudioWorkletNodeClass(
                this.audioContext,
                "capture",
                {
                    numberOfInputs: 1,
                    numberOfOutputs: 0,
                    channelCount: 1,
                },
            );

            this.captureNode.port.addEventListener("message", this.onMessage);
            this.captureNode.port.start();
            this.mediaSource.connect(this.captureNode);
            await this.audioContext.resume();

            if (this.startToken !== startToken) {
                return false;
            }

            return true;
        } catch (error) {
            if (this.startToken !== startToken) {
                return false;
            }

            try {
                await this.stop();
            } catch {
                // Preserve the startup failure; cleanup is best effort here.
            }

            throw error;
        } finally {
            if (this.startToken === startToken) {
                this.startToken = null;
            }
        }
    }

    async stop() {
        const audioContext = this.audioContext;
        const mediaStream = this.mediaStream;

        this.startToken = null;
        this.captureNode?.disconnect();
        this.mediaSource?.disconnect();

        this.captureNode = null;
        this.mediaSource = null;
        this.mediaStream = null;
        this.audioContext = null;

        for (const track of mediaStream?.getTracks() ?? []) {
            track.stop();
        }

        if (audioContext && audioContext.state !== "closed") {
            await audioContext.close();
        }
    }
}
