export const AUDIO_FRAME_TYPE = 1;
export const AUDIO_HEADER_BYTES = 12;

const AUDIO_FLAGS = 0;
const MAX_SAMPLE_COUNT = 0xffff;

export function buildAudioFrame(samples, firstSampleIndex) {
    if (!(samples instanceof Int16Array)) {
        throw new TypeError("Audio samples must be an Int16Array");
    }

    if (
        samples.length === 0 || samples.length > MAX_SAMPLE_COUNT
    ) {
        throw new RangeError(
            "Audio frame must contain between 1 and 65535 samples"
        );
    }

    if (
        !Number.isSafeInteger(firstSampleIndex) || firstSampleIndex < 0
    ) {
        throw new RangeError(
            "First sample index must be a non-negative safe integer"
        );
    }

    const buffer = new ArrayBuffer(
        AUDIO_HEADER_BYTES + samples.length * 2
    );
    const view = new DataView(buffer);

    view.setUint8(0, AUDIO_FRAME_TYPE);
    view.setUint8(1, AUDIO_FLAGS);
    view.setUint16(2, samples.length, true);
    view.setBigUint64(
        4,
        BigInt(firstSampleIndex),
        true
    );

    for (let index = 0; index < samples.length; index += 1) {
        view.setInt16(
            AUDIO_HEADER_BYTES + index * 2,
            samples[index],
            true
        );
    }

    return buffer;
}