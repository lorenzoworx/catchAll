function sampleToSeconds(sample, sampleRate) {
    return sample / sampleRate;
}

export function buildTranscriptDocument({
    committedSegments,
    plainCaptions,
    sampleRate = 16000,
}) {
    if (!Number.isFinite(sampleRate) || sampleRate <= 0){
        throw new RangeError("sampleRate must be positive");
    }

    const finalizedSegments = committedSegments.map((segment) => ({
        text: segment.text.trim(),
        startSeconds: sampleToSeconds(segment.startSample, sampleRate),
        endSeconds: sampleToSeconds(segment.endSample, sampleRate),
    }));

    const acceptedAlternatives = plainCaptions
        .filter((caption) => caption.status === "simplified")
        .map((caption) => ({
                            original: caption.original.trim(),
                            text: caption.text.trim(),
                            startSeconds: sampleToSeconds(caption.startSample, sampleRate),
                            endSeconds: sampleToSeconds(caption.endSample, sampleRate)
            }));

        return {
            formatVersion: 1,
            sampleRate,
            verbatim: finalizedSegments
                .map((segment) => segment.text)
                .filter(Boolean)
                .join(" "),
            finalizedSegments,
            plainLanguageAlternatives: acceptedAlternatives,
        };
}

export function formatTranscriptText(document) {
    const lines = ["CatchAll finalized transcript", "", "Verbatim", document.verbatim || "(no finalized captions)"];

    if (document.plainLanguageAlternatives.length > 0) {
        lines.push(
            "",
            "Accepted plain-language alternatives"
        );

        for (const alternative of document.plainLanguageAlternatives) {
            lines.push(
                "",
                `Original: ${alternative.original}`,
                `Plain: ${alternative.text}`,
            );
        }
    }

    return `${lines.join("\n")}\n`
}

export function makeTranscriptFilename(date = new Date()) {
    const timestamp = date
        .toISOString()
        .replaceAll(":", "-")
        .replaceAll(".", "-");

    return `catchall-transcript-${timestamp}.txt`;
}

