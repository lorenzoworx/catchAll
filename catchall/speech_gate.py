from collections.abc import Sequence
from math import fsum, sqrt


class EnergySpeechGate:
    def __init__(self, threshold: float = 0.01, frame_samples: int = 320, lookback_samples: int = 8_000, min_active_frames: int = 2) -> None:
        if threshold < 0:
            raise ValueError("Threshold cannot be negative")

        if frame_samples <= 0:
            raise ValueError("Frame size must be positive")

        if lookback_samples < frame_samples:
            raise ValueError("Lookback must contain at least one frame")

        if min_active_frames <= 0:
            raise ValueError("Minimum active frames must be positive")

        if (min_active_frames * frame_samples > lookback_samples):
            raise ValueError("Lookback is too short for active-frame count")

        self._threshold = threshold
        self._frame_samples = frame_samples
        self._lookback_samples = lookback_samples
        self._min_active_frames = min_active_frames

    def has_speech(self, samples: Sequence[float]) -> bool:
        recent = samples[-self._lookback_samples :]
        active_frames = 0

        for offset in range(0, len(recent), self._frame_samples):
            frame = recent[offset : offset + self._frame_samples]

            if len(frame) < self._frame_samples:
                continue

            mean_square = fsum(sample * sample for sample in frame) / len(frame)
            rms = sqrt(mean_square)

            if rms >= self._threshold:
                active_frames += 1

                if(active_frames >= self._min_active_frames):
                    return True

        return False