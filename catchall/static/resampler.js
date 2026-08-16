export class StreamingResampler {
    constructor(inputRate, outputRate) {
        if (
            !Number.isFinite(inputRate) ||
            !Number.isFinite(outputRate) ||
            inputRate <= 0 ||
            outputRate <= 0
        ) {
            throw new RangeError("Sample rates must be positive numbers");
        }

        this.ratio = inputRate / outputRate;
        this.position = 0;
        this.carry = new Float32Array(0);
    }

    process(input) {
        if (!(input instanceof Float32Array)) {
            throw new TypeError("Resampler input must be a Float32Array");
        }

        if (input.length === 0) {
            return new Float32Array(0);
        }

        const source = new Float32Array(
            this.carry.length + input.length
        );
        
        source.set(this.carry);
        source.set(input, this.carry.length);

        const output = [];
        let position = this.position;

        while(position + this.ratio <= source.length) {
            const end = position + this.ratio;
            let cursor = position;
            let weightedSum = 0;

            while (cursor < end) {
                const sourceIndex = Math.floor(cursor);
                const segmentEnd = Math.min(
                    end,
                    sourceIndex + 1
                );
                const weight = segmentEnd - cursor;

                weightedSum += source[sourceIndex] * weight;
                cursor = segmentEnd;
            }

            output.push(weightedSum / this.ratio);
            position = end;
        }

        const consumed = Math.floor(position);

        this.carry = source.slice(consumed);
        this.position = position - consumed;

        return Float32Array.from(output);
    }
}

export function floatToInt16(sample) {
    const clamped = Math.max(-1, Math.min(1, sample));

    if (clamped < 0) {
        return Math.round(clamped * 32768);
    }

    return Math.round(clamped * 32767);
}