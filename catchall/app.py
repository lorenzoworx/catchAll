import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from catchall import _core
from catchall.audio_consumer import AudioConsumer
from catchall.audio_protocol import AudioFrameError, decode_audio_frame
from catchall.local_agreement import LocalAgreement
from catchall.nli import BidirectionalNliScorer
from catchall.plain_language import RuleBasedSimplifier
from catchall.recognition import RecognitionPipeline, TranscriptCandidate
from catchall.recognizer_provider import RecognizerProvider
from catchall.rewrite_guard import (
    BidirectionalEntailmentGuard,
    CompositeGuard,
    ContrastGuard,
    FaithfulnessGuard,
)
from catchall.sentence_assembler import SentenceAssembler
from catchall.simplification import SimplificationPipeline, SimplificationResult
from catchall.speech_gate import EnergySpeechGate
from catchall.whisper_recognizer import WhisperRecognizer

SAMPLE_RATE = 16_000
RING_SECONDS = 10
RING_CAPACITY = SAMPLE_RATE * RING_SECONDS
_SHARED_NLI_SCORER = BidirectionalNliScorer()

_SHARED_PLAIN_LANGUAGE_GUARD = CompositeGuard(
    FaithfulnessGuard(),
    ContrastGuard(),
    BidirectionalEntailmentGuard(
        scorer=_SHARED_NLI_SCORER,
        minimum_entailment=0.80,
        maximum_contradiction=0.20
    )
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="CatchAll")
app.state.recognizer_provider = RecognizerProvider(
    WhisperRecognizer
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
def inded() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

@app.websocket("/ws")
async def caption_socket(websocket: WebSocket) -> None:
    ring = _core.AudioRing(RING_CAPACITY)

    agreement = LocalAgreement()

    received_samples = 0
    rejected_frames = 0

    send_lock = asyncio.Lock()

    async def send_message(message: dict[str, object]) -> None:
        async with send_lock:
            await websocket.send_json(message)

    await websocket.accept()

    await send_message(
        {
            "type": "connection",
            "status": "connected",
        }
    )

    await send_message(
        {
            "type": "recognizer",
            "status": "loading",
        }
    )

    try:
        recognizer = await websocket.app.state.recognizer_provider.get()
    except Exception as error:  #noqa: BLE001
                                # Model loading can raise several third-party exception types. So we convert them into one stable WebSocket error response
        await send_message(
            {
                "type": "error",
                "code": "recognizer_unavailable",
                "message": f"{type(error).__name__}: {error}",
            }
        )
        await websocket.close(code=1011)
        return

    await send_message(
        {
            "type": "recognizer",
            "status": "ready",
        }
    )

    recognition_messages: asyncio.Queue[dict[str, object]] = asyncio.Queue()

    plain_language_enabled = False
    sentence_assembler = SentenceAssembler()

    def on_simplification_result(result: SimplificationResult) -> None:
        recognition_messages.put_nowait({
          "type": "plain_caption",
            "sentence_id": result.sentence_id,
            "text": result.text,
            "original": result.original,
            "status": result.status,
            "start_sample": result.start_sample,
            "end_sample": result.end_sample,  
        })

    simplification_pipeline = SimplificationPipeline(
        simplifier=RuleBasedSimplifier(),
        guard=_SHARED_PLAIN_LANGUAGE_GUARD,
        on_result=on_simplification_result,
    )

    def on_candidate(candidate: TranscriptCandidate) -> None:
        result = agreement.update(candidate.words)

        if result.committed:
            recognition_messages.put_nowait({
                "type": "caption",
                "state": "committed",
                "text": " ".join(word.text for word in result.committed),
                "start_sample": result.committed[0].start_sample,
                "end_sample": result.committed[-1].end_sample,
            })

        completed_sentences = sentence_assembler.add(result.committed)

        if plain_language_enabled:
            for sentence in completed_sentences:
                simplification_pipeline.accept(sentence)

        recognition_messages.put_nowait({
            "type": "caption",
            "state": "provisional",
            "text": " ".join(word.text for word in result.provisional),
            "window_start_sample": candidate.window_start_sample,
            "window_end_sample": candidate.window_end_sample,
        })

    def on_recognition_error(message: str) -> None:
        recognition_messages.put_nowait({
            "type": "error",
            "code": "recognition_failed",
            "message": message,
        })

    pipeline = RecognitionPipeline(
        recognizer=recognizer,
        on_candidate=on_candidate,
        on_error=on_recognition_error,
        speech_gate=EnergySpeechGate(),
    )

    def accept_audio(samples: list[float]) -> None:
        pipeline.accept_audio(samples)

    consumer = AudioConsumer(
        ring,
        chunk_samples=320,
        on_chunk=accept_audio,
    )

    async def forward_recognition_messages() -> None:
        while True:
            message = await recognition_messages.get()

            try:
                await send_message(message)
            finally:
                recognition_messages.task_done()

    tasks = [
        asyncio.create_task(consumer.run()),
        asyncio.create_task(pipeline.run()),
        asyncio.create_task(simplification_pipeline.run()),
        asyncio.create_task(forward_recognition_messages()),
    ]

    try:
        while True:
            incoming = await websocket.receive()

            if incoming["type"] == "websocket.disconnect":
                break

            binary = incoming.get("bytes")

            if binary is not None:
                try:
                    frame = decode_audio_frame(binary)
                except AudioFrameError as error:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "invalid_audio_frame",
                            "message": str(error),
                        }
                    )
                    continue

                received_samples += len(frame.samples)
                accepted = ring.write(frame.samples)

                if accepted > 0:
                    consumer.notify()
                    await asyncio.sleep(0)

                if accepted != len(frame.samples):
                    rejected_frames += 1

                    await send_message(
                       {
                            "type": "error",
                            "code": "audio_buffer_full",
                            "dropped_samples": len(frame.samples) - accepted,
                        }
                    )
                continue

            text = incoming.get("text")

            if text is None:
                continue

            try:
                message = json.loads(text)
            except json.JSONDecodeError:
                await send_message(
                    {
                        "type": "error",
                        "code": "invalid_json",
                        "message": "Control message is not valid JSON.",
                    }
                )
                continue

            if message.get("type") == "ping":
                await send_message({"type": "pong"})
            elif message.get("type") == "stats":
                buffered_samples = ring.size

                await send_message(
                    {
                        "type": "stats",
                        "received_samples": received_samples,
                        "consumed_samples": consumer.consumed_samples,
                        "buffered_samples": buffered_samples,
                        "buffered_seconds": buffered_samples / SAMPLE_RATE,
                        "dropped_samples": ring.dropped_samples,
                        "rejected_frames": rejected_frames,
                        "pending_recognition_windows": pipeline.pending_windows,
                        "rejected_recognition_windows": pipeline.rejected_windows,
                        "failed_recognition_windows": pipeline.failed_windows,
                        "skipped_silence_windows": pipeline.skipped_silence_windows,
                        "committed_words": agreement.committed_word_count,
                        "final_silence_windows": pipeline.final_silence_windows,
                        "silence_boundaries": pipeline.silence_boundaries,
                        "plain_language_enabled": plain_language_enabled,
                        "processed_plain_sentences": simplification_pipeline.processed_sentences,
                        "fallback_plain_sentences": simplification_pipeline.fallback_sentences,
                        "rejected_plain_sentences": simplification_pipeline.rejected_sentences
                    }
                )
            elif message.get("type") == "plain_language":
                enabled = message.get("enabled")

                if not isinstance(enabled, bool):
                    await send_message({
                        "type": "error",
                        "code": "invalid_plain_language_setting",
                        "message": "enabled must be a boolean."
                    })
                    continue

                plain_language_enabled = enabled

                await send_message({
                    "type": "plain_language",
                    "enabled": plain_language_enabled,
                    "processing": "local"
                })
            else:
                await send_message(
                    {
                        "type": "error",
                        "code": "unknown_message",
                        "message": "Unknown message type.",
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()

        await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )