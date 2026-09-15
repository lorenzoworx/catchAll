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
