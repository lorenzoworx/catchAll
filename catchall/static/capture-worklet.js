import { StreamingResampler, floatToInt16 } from "./resampler.js";

const TARGET_SAMPLE_RATE = 16_000;
const FRAME_SAMPLES = 320;

class CaptureProcessor extends AudioWorkletProcessor {
    constructor() {
        super();

        this.resampler = sampleRate === TARGET_SAMPLE_RATE ? null : new StreamingResampler(
            sampleRate,
            TARGET_SAMPLE_RATE
        );

        this.frame = new Int16Array(FRAME_SAMPLES);
        this.frameOffset = 0;

        this.totalOutputSamples = 0;
        this.lastReportedSamples = 0;
        this.nextFrameSampleIndex = 0;

        this.port.postMessage({
            type: "ready",
            inputSampleRate: sampleRate,
            outputSampleRate: TARGET_SAMPLE_RATE,
            frameSamples: FRAME_SAMPLES,
        });
    }

    process(inputs) {
        const channel = inputs[0]?.[0];

        if (!channel) {
            return true;
        }

        const output = this.resampler ? this.resampler.process(channel) : channel;

        this.totalOutputSamples += output.length;

        for (const sample of output) {
            this.frame[this.frameOffset] = floatToInt16(sample);
            this.frameOffset += 1;

            if (this.frameOffset === FRAME_SAMPLES) {
                const completedFrame = this.frame;

                this.port.postMessage(
                    {
                        type: "audio-frame",
                        firstSampleIndex: this.nextFrameSampleIndex,
                        samples: completedFrame.buffer,
                    },
                    [completedFrame.buffer]
                );

                this.nextFrameSampleIndex += FRAME_SAMPLES;
                this.frame = new Int16Array(FRAME_SAMPLES);
                this.frameOffset = 0;
            }
        }

        if (this.totalOutputSamples - this.lastReportedSamples >= TARGET_SAMPLE_RATE / 2) {
            this.lastReportedSamples = this.totalOutputSamples;

            this.port.postMessage({
                type: "progress",
                framedSamples: this.nextFrameSampleIndex,
                outputSampleRate: TARGET_SAMPLE_RATE,
            });
        }

        return true;
    }
}

registerProcessor("capture", CaptureProcessor);