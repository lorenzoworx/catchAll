from __future__ import annotations

import asyncio

from catchall import _core


class AudioConsumer:
    def __init__(
            self,
            ring: _core.AudioRing,
            chunk_samples: int = 320,
    ) -> None:
        if chunk_samples <= 0:
            raise ValueError("Chunk size must be positive")

        self._ring = ring
        self._chunk_samples = chunk_samples
        self._audio_available = asyncio.Event()

        self.consumed_samples = 0

    def notify(self) -> None:
        self._audio_available.set()

    def drain_available(self) -> int:
        drained_samples = 0

        while self._ring.size >= self._chunk_samples:
            samples = self._ring.read(self._chunk_samples)

            if len(samples) != self._chunk_samples:
                break

            drained_samples += len(samples)
            self.consumed_samples += len(samples)

        return drained_samples

    async def run(self) -> None:
        while True:
            await self._audio_available.wait()
            self._audio_available.clear()
            self.drain_available()