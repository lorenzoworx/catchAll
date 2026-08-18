from __future__ import annotations

import asyncio
from collections.abc import Callable

from catchall import _core

AudioChunkHandler = Callable[[list[float]], None]


class AudioConsumer:
    def __init__(self, ring: _core.AudioRing, chunk_samples: int = 320, on_chunk:AudioChunkHandler | None = None,) -> None:
        if chunk_samples <= 0:
            raise ValueError("Chunk size must be positive")

        self._ring = ring
        self._chunk_samples = chunk_samples
        self._audio_available = asyncio.Event()
        self._on_chunk = on_chunk

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

            if self._on_chunk is not None:
                self._on_chunk(samples)

        return drained_samples

    async def run(self) -> None:
        while True:
            await self._audio_available.wait()
            self._audio_available.clear()
            self.drain_available()