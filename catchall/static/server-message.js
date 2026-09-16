const CAPTION_STATES = new Set(["committed", "provisional"]);
const CAPTURE_STATES = new Set(["finalized"]);
const CONNECTION_STATES = new Set(["connected"]);
const PLAIN_CAPTION_STATES = new Set(["fallback", "simplified", "unchanged"]);
const RECOGNIZER_STATES = new Set(["loading", "ready"]);

export const INVALID_SERVER_MESSAGE_NOTICE =
    "A server update was invalid and was ignored. Captioning can continue.";

export class ServerMessageError extends Error {
    constructor(message) {
        super(message);
        this.name = "ServerMessageError";
    }
}

function requireRecord(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
        throw new ServerMessageError("Server message must be a JSON object.");
    }
}

function requireString(message, field) {
    if (typeof message[field] !== "string" || message[field].length === 0) {
        throw new ServerMessageError(`${field} must be a non-empty string.`);
    }
}

function requireText(message, field) {
    if (typeof message[field] !== "string") {
        throw new ServerMessageError(`${field} must be a string.`);
    }
}

function requireBoolean(message, field) {
    if (typeof message[field] !== "boolean") {
        throw new ServerMessageError(`${field} must be a boolean.`);
    }
}

function requireSample(message, field) {
    if (!Number.isInteger(message[field]) || message[field] < 0) {
        throw new ServerMessageError(`${field} must be a non-negative integer.`);
    }
}

function requireAllowed(message, field, allowed) {
    requireString(message, field);

    if (!allowed.has(message[field])) {
        throw new ServerMessageError(`${field} has an unsupported value.`);
    }
}

function validateCaption(message) {
    requireAllowed(message, "state", CAPTION_STATES);
    requireText(message, "text");

    if (message.state === "committed") {
        requireSample(message, "start_sample");
        requireSample(message, "end_sample");
        return;
    }

    requireSample(message, "window_start_sample");
    requireSample(message, "window_end_sample");
}

function validatePlainCaption(message) {
    requireString(message, "sentence_id");
    requireString(message, "text");
    requireString(message, "original");
    requireAllowed(message, "status", PLAIN_CAPTION_STATES);
    requireSample(message, "start_sample");
    requireSample(message, "end_sample");
}

function validateKnownMessage(message) {
    if (message.type === "connection") {
        requireAllowed(message, "status", CONNECTION_STATES);
    } else if (message.type === "recognizer") {
        requireAllowed(message, "status", RECOGNIZER_STATES);
    } else if (message.type === "error") {
        requireString(message, "code");
    } else if (message.type === "caption") {
        validateCaption(message);
    } else if (message.type === "plain_language") {
        requireBoolean(message, "enabled");
    } else if (message.type === "plain_caption") {
        validatePlainCaption(message);
    } else if (message.type === "capture") {
        requireAllowed(message, "status", CAPTURE_STATES);
    }
}

export function parseServerMessage(data) {
    if (typeof data !== "string") {
        throw new ServerMessageError("Server message must be text.");
    }

    let message;

    try {
        message = JSON.parse(data);
    } catch {
        throw new ServerMessageError("Server message is not valid JSON.");
    }

    requireRecord(message);
    requireString(message, "type");
    validateKnownMessage(message);

    return message;
}
