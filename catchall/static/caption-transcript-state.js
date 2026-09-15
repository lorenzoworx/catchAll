export class CaptionTranscriptState {
    constructor() {
        this.committedSegments = [];
        this.plainCaptions = new Map();
        this.hasPlainCaptions = false;
    }

    get hasCommittedCaptions() {
        return this.committedSegments.length > 0;
    }

    recordCommitted(message) {
        const firstCaption = !this.hasCommittedCaptions;
        const segment = {
            text: message.text,
            startSample: message.start_sample,
            endSample: message.end_sample,
        };

        this.committedSegments.push(segment);

        return { firstCaption, segment };
    }

    recordPlain(message, captionKey) {
        const firstCaption = !this.hasPlainCaptions;
        const caption = {
            original: message.original,
            text: message.text,
            status: message.status,
            startSample: message.start_sample,
            endSample: message.end_sample,
        };

        this.hasPlainCaptions = true;

        if (message.status === "simplified") {
            this.plainCaptions.set(captionKey, caption);
        } else {
            this.plainCaptions.delete(captionKey);
        }

        return { firstCaption, caption };
    }

    resetPlainDisplay() {
        this.hasPlainCaptions = false;
    }

    clear() {
        this.committedSegments.length = 0;
        this.plainCaptions.clear();
        this.hasPlainCaptions = false;
    }
}
