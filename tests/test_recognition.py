import asyncio
from collections.abc import Sequence
from contextlib import suppress

from catchall.recognition import RecognitionPipeline
from catchall.recognition_window import RecognitionWindowBuffer


class FakeRecognizer:
    def __init__(self, result: str = "hello world") -> None:
        self.result = result
        self.calls: list[tuple[float, ...]] = []

    def transcribe(self, samples: Sequence[float]) -> str:
        snapshot = tuple(samples)
        self.calls.append(snapshot)

        return self.result

def test_audio_window_produces_transcript_candidate() -> None:
    async def scenario() -> None:
        candidates = []
        recognizer = FakeRecognizer()

        pipeline = RecognitionPipeline(
            recognizer=recognizer,
            on_candidate=candidates.append,
            window_buffer=RecognitionWindowBuffer(
                min_samples=4,
                max_samples=8,
                hop_samples=2,
            ),
        )
        task = asyncio.create_task(pipeline.run())

        try:
            assert pipeline.accept_audio(range(4)) == 1

            await pipeline.wait_until_idle()

            assert recognizer.calls == [
                (0.0, 1.0, 2.0, 3.0)
            ]
            assert len(candidates) == 1
            assert candidates[0].text == "hello world"
            assert candidates[0].window_start_sample == 0
            assert candidates[0].window_end_sample == 4
        finally:
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario())

def test_empty_transcript_is_not_emitted() -> None:
    async def scenario() -> None:
        candidates = []

        pipeline = RecognitionPipeline(
            recognizer=FakeRecognizer(" "),
            on_candidate=candidates.append,
            window_buffer=RecognitionWindowBuffer(
                min_samples=4,
                max_samples=8,
                hop_samples=2,
            ),
        )
        task = asyncio.create_task(pipeline.run())

        try:
            pipeline.accept_audio(range(4))
            await pipeline.wait_until_idle()

            assert candidates == []
        finally:
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario()) 

def test_rejects_windows_when_queue_is_full() -> None:
    pipeline = RecognitionPipeline(
        recognizer=FakeRecognizer(),
        on_candidate=lambda candidate: None,
        window_buffer=RecognitionWindowBuffer(
            min_samples=4,
            max_samples=8,
            hop_samples=2
        ),
        max_pending_windows=1,
    )

    assert pipeline.accept_audio(range(6)) == 1
    assert pipeline.pending_windows == 1
    assert pipeline.rejected_windows == 1

def test_reports_recognizer_failures() -> None:
    class BrokenRecognizer:
        def transcribe(self, samples: Sequence[float]) -> str:
            raise RuntimeError("recognition failed")

    async def scenario() -> None:
        errors = []

        pipeline = RecognitionPipeline(
            recognizer=BrokenRecognizer(),
            on_candidate=lambda candidate: None,
            on_error=errors.append,
            window_buffer=RecognitionWindowBuffer(
                min_samples=4,
                max_samples=8,
                hop_samples=2,
            ),
        )
        task = asyncio.create_task(pipeline.run())

        try:
            pipeline.accept_audio(range(4))
            await pipeline.wait_until_idle()

            assert pipeline.failed_windows == 1
            assert errors == ["RuntimeError: recognition failed"]

        finally:
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario())