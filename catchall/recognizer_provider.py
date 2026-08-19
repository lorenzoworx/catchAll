from __future__ import annotations

import asyncio
from collections.abc import Callable

from catchall.recognition import Recognizer

RecognizerFactory = Callable[[], Recognizer]

class RecognizerProvider:
    def __init__(self, factory: RecognizerFactory) -> None:
        self._factory = factory
        self._recognizer: Recognizer | None = None
        self._lock = asyncio.Lock()

    @property
    def loaded(self) -> bool:
        return self._recognizer is not None

    async def get(self) -> Recognizer:
        if self._recognizer is not None:
            return self._recognizer

        async with self._lock:
            if self._recognizer is None:
                self._recognizer = await asyncio.to_thread(
                    self._factory
                )

        return self._recognizer