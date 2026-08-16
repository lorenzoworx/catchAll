class CaptureProcessor extends AudioWorkletProcessor {
    constructor() {
        super();

        this.totalSamples = 0;
        this.lastReportedSamples = 0;

        this.port.postMessage({
            type: "ready",
            sampleRate,
        });
    }

    process(inputs) {
        const channel = inputs[0]?.[0];

        if (!channel) {
            return true;
        }

        this.totalSamples += channel.length;

        if (this.totalSamples - this.lastReportedSamples >= sampleRate / 2) {
            this.lastReportedSamples = this.totalSamples;

            this.port.postMessage({
                type: "progress",
                totalSamples: this.totalSamples,
                sampleRate,
            });
        }

        return true;
    }
}

registerProcessor("capture", CaptureProcessor);