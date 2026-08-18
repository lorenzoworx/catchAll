from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

SAMPLE_RATE = 16_000
MIN_WINDOW_SAMPLES = SAMPLE_RATE
MAX_WINDOW_SAMPLES = SAMPLE_RATE * 5
HOP_SAMPLES = SAMPLE_RATE // 2

@dataclass(frozen=True)
class AudioWindow:
    start_sample: int
    end_sample: int
    samples: tuple[float, ...]

class RecognitionWindowBuffer:
    def __init__(
            self,
            min_samples: int = MIN_WINDOW_SAMPLES,
            max_samples: int = MAX_WINDOW_SAMPLES,
            hop_samples: int = HOP_SAMPLES,
    ) -> None:
        if min_samples <= 0:
            raise ValueError("Minimum window must be positive")

        if max_samples < min_samples:
            raise ValueError("Maximum window cannot be smaller than minimum")

        if hop_samples <= 0:
            raise ValueError("Hop size must be positive")

        self._samples: deque[float] = deque(maxlen=max_samples)
        self._total_samples = 0
        self._next_emission = min_samples
        self._hop_samples = hop_samples

    def add(self, samples: Iterable[float]) -> list[AudioWindow]:
        windows: list[AudioWindow] = []

        for sample in samples:
            self._samples.append(float(sample))
            self._total_samples += 1

            if self._total_samples < self._next_emission:
                continue

            snapshot = tuple(self._samples)

            windows.append(
                AudioWindow(
                    start_sample=(
                        self._total_samples - len(snapshot)
                    ),
                    end_sample=self._total_samples,
                    samples=snapshot,
                )
            )

            self._next_emission += self._hop_samples

        return windows