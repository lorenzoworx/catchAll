import asyncio
from contextlib import suppress

from catchall.recognition import TimedWord
from catchall.sentence_assembler import CommittedSentence
from catchall.simplification import SimplificationPipeline


class FixedSimplifier:
    def __init__(self, result: str) -> None:
        self.result = result

    def simplify(self, text: str) -> str:
        return self.result


class BrokenSimplifier:
    def simplify(self, text: str) -> str:
        raise RuntimeError("simplifier failed")


class AcceptingGuard:
    def accepts(self, original: str, candidate: str) -> bool:
        return True


class RejectingGuard:
    def accepts(self, original: str, candidate: str) -> bool:
        return False


def make_sentence() -> CommittedSentence:
    return CommittedSentence(
        words=(
            TimedWord("The", 0, 100),
            TimedWord("meeting", 100, 200),
            TimedWord("begins.", 200, 300),
        )
    )


def test_approved_rewrite_is_returned() -> None:
    async def scenario() -> None:
        results = []
        pipeline = SimplificationPipeline(
            simplifier=FixedSimplifier("The meeting starts."),
            guard=AcceptingGuard(),
            on_result=results.append,
        )
        task = asyncio.create_task(pipeline.run())

        try:
            assert pipeline.accept(make_sentence()) is True
            await pipeline.wait_until_idle()

            assert len(results) == 1
            assert results[0].text == "The meeting starts."
            assert results[0].status == "simplified"
            assert pipeline.processed_sentences == 1
            assert pipeline.fallback_sentences == 0
        finally:
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario())


def test_rejected_rewrite_falls_back_to_verbatim() -> None:
    async def scenario() -> None:
        results = []
        pipeline = SimplificationPipeline(
            simplifier=FixedSimplifier("Something different."),
            guard=RejectingGuard(),
            on_result=results.append,
        )
        task = asyncio.create_task(pipeline.run())

        try:
            pipeline.accept(make_sentence())
            await pipeline.wait_until_idle()

            assert results[0].text == "The meeting begins."
            assert results[0].status == "fallback"
            assert pipeline.fallback_sentences == 1
        finally:
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario())


def test_simplifier_error_falls_back_to_verbatim() -> None:
    async def scenario() -> None:
        results = []
        pipeline = SimplificationPipeline(
            simplifier=BrokenSimplifier(),
            guard=AcceptingGuard(),
            on_result=results.append,
        )
        task = asyncio.create_task(pipeline.run())

        try:
            pipeline.accept(make_sentence())
            await pipeline.wait_until_idle()

            assert results[0].text == "The meeting begins."
            assert results[0].status == "fallback"
        finally:
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario())


def test_full_queue_rejects_new_sentence() -> None:
    pipeline = SimplificationPipeline(
        simplifier=FixedSimplifier("Plain text."),
        guard=AcceptingGuard(),
        on_result=lambda result: None,
        max_pending_sentences=1,
    )

    assert pipeline.accept(make_sentence()) is True
    assert pipeline.accept(make_sentence()) is False
    assert pipeline.rejected_sentences == 1