from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from catchall.sentence_assembler import CommittedSentence

SimplificationStatus = Literal[
    "simplified",
    "unchanged",
    "fallback",
]


class Simplifier(Protocol):
    def simplify(self, text: str) -> str:
        """Produce a plain-language candidate."""


class RewriteGuard(Protocol):
    def accepts(self, original: str, candidate: str) -> bool:
        """Return True only when the candidate is safe to display."""


@dataclass(frozen=True)
class SimplificationResult:
    sentence_id: str
    original: str
    text: str
    status: SimplificationStatus
    start_sample: int
    end_sample: int

ResultHandler = Callable[[SimplificationResult], None]


class SimplificationPipeline:
    def __init__(self, simplifier: Simplifier, guard: RewriteGuard, on_result: ResultHandler, max_pending_sentences: int = 16) -> None:
        if max_pending_sentences <= 0:
            raise ValueError("max_pending_sentences must be positive")

        self._simplifier = simplifier
        self._guard = guard
        self._on_result = on_result
        self._queue: asyncio.Queue[CommittedSentence] = asyncio.Queue(maxsize=max_pending_sentences)

        self.processed_sentences = 0
        self.fallback_sentences = 0
        self.rejected_sentences = 0

    def accept(self, sentence: CommittedSentence) -> bool:
        try:
            self._queue.put_nowait(sentence)
        except asyncio.QueueFull:
            self.rejected_sentences += 1
            self.fallback_sentences += 1

            sentence_id = f"sentence-{sentence.start_sample}-{sentence.end_sample}"

            self._on_result(self._fallback(sentence, sentence_id))

            return False

        return True

    async def run(self) -> None:
        while True:
            sentence = await self._queue.get()

            try:
                result = await asyncio.to_thread(self._process_sentence, sentence)

                self.processed_sentences += 1

                if result.status == "fallback":
                    self.fallback_sentences += 1

                self._on_result(result)
            finally:
                self._queue.task_done()

    async def wait_until_idle(self) -> None:
        await self._queue.join()

    def _process_sentence(self, sentence: CommittedSentence) -> SimplificationResult:
        original = sentence.text
        sentence_id = f"sentence-{sentence.start_sample}-{sentence.end_sample}"

        try:
            candidate = self._simplifier.simplify(original).strip()

            if not candidate:
                return self._fallback(sentence, sentence_id)

            if candidate == original:
                return SimplificationResult(
                    sentence_id=sentence_id,
                    original=original,
                    text=original,
                    status="unchanged",
                    start_sample=sentence.start_sample,
                    end_sample=sentence.end_sample,
                )

            if not self._guard.accepts(original, candidate):
                return self._fallback(sentence, sentence_id)

            return SimplificationResult(
                sentence_id=sentence_id,
                original=original,
                text=candidate,
                status="simplified",
                start_sample=sentence.start_sample,
                end_sample=sentence.end_sample,
            )
        except Exception:   #noqa: BLE001
            return self._fallback(sentence, sentence_id)

    @staticmethod
    def _fallback(sentence: CommittedSentence, sentence_id: str) -> SimplificationResult:
        return SimplificationResult(
            sentence_id=sentence_id,
            original=sentence.text,
            text=sentence.text,
            status="fallback",
            start_sample=sentence.start_sample,
            end_sample=sentence.end_sample,
        )