import asyncio
import threading
from collections.abc import Sequence

import pytest

from catchall.recognition import RecognitionHypothesis, TimedWord
from catchall.recognizer_provider import RecognizerProvider


class FakeRecognizer:
    def transcribe(self, samples: Sequence[float]) -> RecognitionHypothesis:
        return RecognitionHypothesis(words=(TimedWord(
            text="test",
            start_sample=0,
            end_sample=len(samples)
        ),))

def test_loads_recognizer_only_once() -> None:
    async def scenario() -> None:
        recognizer = FakeRecognizer()
        factory_calls = 0

        def factory() -> FakeRecognizer:
            nonlocal factory_calls
            factory_calls += 1

            return recognizer

        provider = RecognizerProvider(factory)

        first, second, third = await asyncio.gather(
            provider.get(),
            provider.get(),
            provider.get(),
        )

        assert first is recognizer
        assert second is recognizer
        assert third is recognizer
        assert factory_calls == 1
        assert provider.loaded is True

    asyncio.run(scenario())

def test_loads_recognizer_off_event_loop_thread() -> None:
    async def scenario() -> None:
        event_loop_thread = threading.get_ident()
        factory_thread: int | None = None

        def factory() -> FakeRecognizer:
            nonlocal factory_thread
            factory_thread = threading.get_ident()

            return FakeRecognizer()

        provider = RecognizerProvider(factory)

        await provider.get()

        assert factory_thread is not None
        assert factory_thread != event_loop_thread

    asyncio.run(scenario())

def test_failed_load_can_be_retried() -> None:
    async def scenario() -> None:
        factory_calls = 0

        def factory() -> FakeRecognizer:
            nonlocal factory_calls
            factory_calls += 1

            if factory_calls == 1:
                raise RuntimeError("model failed to load")

            return FakeRecognizer()
        provider = RecognizerProvider(factory)

        with pytest.raises(
            RuntimeError,
            match="model failed to load",
        ):
            await provider.get()

        recognizer = await provider.get()

        assert isinstance(recognizer, FakeRecognizer)
        assert factory_calls == 2
        assert provider.loaded is True
    asyncio.run(scenario())