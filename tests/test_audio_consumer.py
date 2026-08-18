import asyncio
from contextlib import suppress

from catchall import _core
from catchall.audio_consumer import AudioConsumer


def test_drains_complete_audio_chunks() -> None:
    ring = _core.AudioRing(1_000)
    consumer = AudioConsumer(ring, chunk_samples=320)

    assert ring.write([0.25] * 640) == 640
    assert consumer.drain_available() == 640

    assert ring.size == 0
    assert consumer.consumed_samples == 640

def test_leaves_incomplete_chunk_buffered() -> None:
    ring = _core.AudioRing(1_000)
    consumer = AudioConsumer(ring, chunk_samples=320)

    assert ring.write([0.25] * 400) == 400
    assert consumer.drain_available() == 320

    assert ring.size == 80
    assert consumer.consumed_samples == 320

def test_background_consumer_drains_after_notification() -> None:
    async def scenario() -> None:
        ring = _core.AudioRing(1_000)
        consumer = AudioConsumer(ring, chunk_samples=320)
        task = asyncio.create_task(consumer.run())

        try:
            assert ring.write([0.25] * 320) == 320

            consumer.notify()
            await asyncio.sleep(0)

            assert ring.size == 0
            assert consumer.consumed_samples == 320
        finally:
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario())

def test_delivers_consumed_chunks_to_handler() -> None:
    ring = _core.AudioRing(1_000)
    delivered: list[list[float]] = []

    consumer = AudioConsumer(
        ring,
        chunk_samples=320,
        on_chunk=delivered.append,
    )

    assert ring.write([0.25] * 320) == 320
    assert consumer.drain_available() == 320

    assert delivered == [[0.25] * 320]