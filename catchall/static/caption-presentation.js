// Presentation only: neither helper changes audio or transcript content.
export function microphoneLevel(samples) {
    if (!samples.length) return 0;
    let squared = 0;
    for (const sample of samples) squared += (sample / 32768) ** 2;
    return Math.min(1, Math.sqrt(squared / samples.length) * 5);
}

export function retrySeconds(deadline, now) {
    return Math.max(0, Math.ceil((deadline - now) / 1000));
}
