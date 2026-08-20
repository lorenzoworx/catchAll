from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from catchall.recognition_window import AudioWindow, RecognitionWindowBuffer


@dataclass(frozen=True)
class TimedWord:
    text: str
    start_sample: int
    end_sample: int

@dataclass(frozen=True)
class RecognitionHypothesis:
    words: tuple[TimedWord, ...]

@dataclass(frozen=True)
class TranscriptCandidate:
    words: tuple[TimedWord, ...]
    window_start_sample: int
    window_end_sample: int

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)

class Recognizer(Protocol):
    def transcribe(self, samples: Sequence[float]) -> RecognitionHypothesis:
        ...

CandidateHandler = Callable[[TranscriptCandidate], None]
ErrorHandler = Callable[[str], None]

class RecognitionPipeline:
    def __init__(
            self,
            recognizer: Recognizer,
            on_candidate: CandidateHandler,
            on_error: ErrorHandler | None = None,
            window_buffer: RecognitionWindowBuffer | None = None,
            max_pending_windows: int = 2,
            speech_gate: SpeechGate | None = None
    ) -> None:
        if max_pending_windows <= 0:
            raise ValueError("Pending-window capacity must be positive")

        self._recognizer = recognizer
        self._on_candidate = on_candidate
        self._on_error = on_error
        self._window_buffer = window_buffer if window_buffer is not None else RecognitionWindowBuffer()
        self._pending: asyncio.Queue[AudioWindow] = asyncio.Queue(maxsize=max_pending_windows)
        self._speech_gate = speech_gate

        self.rejected_windows = 0
        self.failed_windows = 0
        self.skipped_silence_windows = 0

    @property
    def pending_windows(self) -> int:
        return self._pending.qsize()

    def accept_audio(self, samples: Sequence[float]) -> int:
        queued_windows = 0

        for window in self._window_buffer.add(samples):
            if(self._speech_gate is not None and not self._speech_gate.has_speech(window.samples)):
                self.skipped_silence_windows += 1
                continue
            try:
                self._pending.put_nowait(window)
            except asyncio.QueueFull:
                self.rejected_windows += 1
            else:
                queued_windows += 1

        return queued_windows

    async def wait_until_idle(self) -> None:
        await self._pending.join()

    async def run(self) -> None:
        while True:
            window = await self._pending.get()

            try:
                hypothesis = await asyncio.to_thread(
                    self._recognizer.transcribe,
                    window.samples
                )

                absolute_words = tuple(TimedWord(
                    text=word.text,
                    start_sample=window.start_sample + word.start_sample,
                    end_sample=window.start_sample + word.end_sample
                    )
                    for word in hypothesis.words
                )
                if absolute_words:
                    self._on_candidate(
                        TranscriptCandidate(
                            words=absolute_words,
                            window_start_sample=window.start_sample,
                            window_end_sample=window.end_sample
                        )
                    )

            except Exception as error: #noqa: BLE001
                self.failed_windows += 1

                if self._on_error is not None:
                    self._on_error(f"{type(error).__name__}: {error}")

            finally:
                self._pending.task_done()

class SpeechGate(Protocol):
    def has_speech(self, samples: Sequence[float]) -> bool:
        ...