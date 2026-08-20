import asyncio
from collections.abc import Sequence
from contextlib import suppress

from catchall.recognition import RecognitionHypothesis, RecognitionPipeline, TimedWord
from catchall.recognition_window import RecognitionWindowBuffer
from catchall.speech_gate import EnergySpeechGate


class FakeRecognizer:
    def __init__(self, result: str = "hello world") -> None:
        self.result = result
        self.calls: list[tuple[float, ...]] = []

    def transcribe(self, samples: Sequence[float]) -> RecognitionHypothesis:
        snapshot = tuple(samples)
        self.calls.append(snapshot)

        text = self.result.strip()

        if not text:
            return RecognitionHypothesis(words=())

        return RecognitionHypothesis(words=(TimedWord(
            text=text,
            start_sample=0,
            end_sample=len(snapshot),
            
        ),))

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
        def transcribe(self, samples: Sequence[float]) -> RecognitionHypothesis:
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

def test_silence_does_not_queue_recognition() -> None:
    pipeline = RecognitionPipeline(
        recognizer=FakeRecognizer(),
        on_candidate=lambda candidate: None,
        window_buffer=RecognitionWindowBuffer(min_samples=4, max_samples=8, hop_samples=2),
        speech_gate=EnergySpeechGate(threshold=0.05, frame_samples=2, lookback_samples=4, min_active_frames=1)
    )

    assert pipeline.accept_audio([0.0] * 4) == 0
    assert pipeline.pending_windows == 0
    assert pipeline.skipped_silence_windows == 1

def test_active_audio_queues_recognition() -> None:
    pipeline = RecognitionPipeline(
        recognizer=FakeRecognizer(),
        on_candidate=lambda candidate: None,
        window_buffer=RecognitionWindowBuffer(min_samples=4, max_samples=8, hop_samples=2),
        speech_gate=EnergySpeechGate(threshold=0.05, frame_samples=2, lookback_samples=4, min_active_frames=1)
        )
    assert pipeline.accept_audio([0.1] * 4) == 1
    assert pipeline.pending_windows == 1
    assert pipeline.skipped_silence_windows == 0