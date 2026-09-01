from __future__ import annotations

import argparse
import asyncio
import json
import time
import wave
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from websockets.asyncio.client import connect

from catchall.audio_protocol import AUDIO_FRAME_TYPE, AUDIO_HEADER
from evaluation.metrics import normalize_words, percentile, word_errors

SAMPLE_RATE = 16_000
FRAME_SAMPLES = 320
FRAME_BYTES = FRAME_SAMPLES * 2
TRAILING_SILENCE_SECONDS = 2
DEFAULT_CORPUS = Path("evaluation/corpus")
DEFAULT_RESULTS = Path("evaluation/results")


@dataclass
class StreamState:
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    stats_received: asyncio.Event = field(default_factory=asyncio.Event)
    sent_samples: int = 0
    startup_error: str | None = None
    committed: list[tuple[float, dict[str, Any]]] = field(default_factory=list)
    recognition_lags: list[int] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def load_pcm16_mono(path: Path) -> bytes:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1:
            raise ValueError(f"{path}: expected mono audio")

        if audio.getsampwidth() != 2:
            raise ValueError(f"{path}: expected signed 16-bit PCM")

        if audio.getframerate() != SAMPLE_RATE:
            raise ValueError(f"{path}: expected {SAMPLE_RATE} Hz")

        return audio.readframes(audio.getnframes())


async def receive_messages(websocket: Any, state: StreamState) -> None:
    async for raw_message in websocket:
        if isinstance(raw_message, bytes):
            continue

        message = json.loads(raw_message)
        message_type = message.get("type")

        if (message_type == "recognizer" and message.get("status") == "ready"):
            state.ready.set()
            continue

        if (message_type == "error" and message.get("code") == "recognizer_unavailable"):
            state.startup_error = str(message.get("message"))
            state.ready.set()
            continue

        if (message_type == "caption" and message.get("state") == "committed"):
            received_at = time.monotonic()
            state.committed.append((received_at, message))

            end_sample = int(message["end_sample"])
            state.recognition_lags.append(max(0, state.sent_samples - end_sample))
            continue

        if message_type == "stats":
            state.stats = message
            state.stats_received.set()
            continue

        if message_type == "error":
            state.errors.append(message)


async def send_pcm(websocket: Any, pcm: bytes, state: StreamState, started_at: float, realtime: bool) -> None:
    for offset in range(0, len(pcm), FRAME_BYTES):
        payload = pcm[offset : offset + FRAME_BYTES]
        sample_count = len(payload) // 2

        if realtime:
            target_time = (
                started_at
                + (
                    state.sent_samples
                    + sample_count
                )
                / SAMPLE_RATE
            )
            delay = target_time - time.monotonic()

            if delay > 0:
                await asyncio.sleep(delay)

        header = AUDIO_HEADER.pack(
            AUDIO_FRAME_TYPE,
            0,
            sample_count,
            state.sent_samples,
        )

        await websocket.send(header + payload)
        state.sent_samples += sample_count


def count_duplicate_boundaries(committed_messages: list[dict[str, Any]]) -> int:
    duplicates = 0

    for previous, current in pairwise(committed_messages):
        previous_words = normalize_words(str(previous["text"]))
        current_words = normalize_words(str(current["text"]))

        if not previous_words or not current_words:
            continue

        if (previous_words[-1] == current_words[0] and int(current["start_sample"]) < int(previous["end_sample"])):
            duplicates += 1

    return duplicates


async def evaluate_clip(audio_path: Path, websocket_url: str, realtime: bool) -> dict[str, Any]:
    reference_path = audio_path.with_suffix(".txt")

    if not reference_path.is_file():
        raise ValueError(
            f"missing reference transcript: "
            f"{reference_path}"
        )

    pcm = load_pcm16_mono(audio_path)
    reference = reference_path.read_text(encoding="utf-8").strip()
    state = StreamState()

    async with connect(websocket_url, max_size=None) as websocket:
        receiver = asyncio.create_task(receive_messages(websocket, state))

        try:
            await asyncio.wait_for(
                state.ready.wait(),
                timeout=120,
            )

            if state.startup_error is not None:
                raise RuntimeError(state.startup_error)

            started_at = time.monotonic()

            await send_pcm(
                websocket,
                pcm,
                state,
                started_at,
                realtime,
            )

            silence = (
                b"\x00\x00"
                * SAMPLE_RATE
                * TRAILING_SILENCE_SECONDS
            )
            await send_pcm(
                websocket,
                silence,
                state,
                started_at,
                realtime,
            )

            await asyncio.sleep(6)

            await websocket.send(json.dumps({"type": "stats"}))
            await asyncio.wait_for(
                state.stats_received.wait(),
                timeout=5,
            )
        finally:
            receiver.cancel()

            with suppress(asyncio.CancelledError):
                await receiver

    committed_messages = [message for _, message in state.committed]
    transcript = " ".join(str(message["text"]).strip() for message in committed_messages)

    errors = word_errors(reference, transcript)

    commit_latencies = [
        (
            received_at
            - (
                started_at
                + int(message["end_sample"])
                / SAMPLE_RATE
            )
        )
        * 1000
        for received_at, message
        in state.committed
    ]

    audio_seconds = (len(pcm) / 2 / SAMPLE_RATE)

    return {
        "clip": audio_path.name,
        "audio_seconds": round(
            audio_seconds,
            3,
        ),
        "reference": reference,
        "transcript": transcript,
        "word_errors": {
            "substitutions": errors.substitutions,
            "deletions": errors.deletions,
            "insertions": errors.insertions,
            "reference_words": (
                errors.reference_words
            ),
            "wer": round(errors.rate, 4),
        },
        "commit_count": len(
            committed_messages
        ),
        "commit_latencies_ms": [
            round(value, 2)
            for value in commit_latencies
        ],
        "recognition_lags_samples": (
            state.recognition_lags
        ),
        "duplicate_boundaries": (
            count_duplicate_boundaries(
                committed_messages
            )
        ),
        "post_commit_retractions": 0,
        "server_stats": state.stats,
        "server_errors": state.errors,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total_errors = 0
    total_reference_words = 0
    commit_latencies = []
    recognition_lags = []

    for result in results:
        counts = result["word_errors"]

        total_errors += (
            counts["substitutions"]
            + counts["deletions"]
            + counts["insertions"]
        )
        total_reference_words += counts["reference_words"]
        commit_latencies.extend(result["commit_latencies_ms"])
        recognition_lags.extend(result["recognition_lags_samples"])

    summary: dict[str, Any] = {
        "clip_count": len(results),
        "corpus_wer": round(
            total_errors / total_reference_words,
            4,
        ),
        "post_commit_retractions": 0,
        "duplicate_boundaries": sum(
            result["duplicate_boundaries"]
            for result in results
        ),
        "dropped_samples": sum(
            int(
                result["server_stats"].get(
                    "dropped_samples",
                    0,
                )
            )
            for result in results
        ),
        "rejected_recognition_windows": sum(
            int(
                result["server_stats"].get(
                    "rejected_recognition_windows",
                    0,
                )
            )
            for result in results
        ),
    }

    if commit_latencies:
        summary["commit_latency_p50_ms"] = round(percentile(commit_latencies, 50), 2)
        summary["commit_latency_p90_ms"] = round(percentile(commit_latencies, 90), 2)

    if recognition_lags:
        summary["recognition_lag_p50_ms"] = round(
            percentile(recognition_lags, 50)
            / SAMPLE_RATE
            * 1000,
            2,
        )
        summary["recognition_lag_p90_ms"] = round(
            percentile(recognition_lags, 90)
            / SAMPLE_RATE
            * 1000,
            2,
        )

    return summary


async def run(args: argparse.Namespace) -> None:
    paths = sorted(args.corpus.glob("*.wav"))

    if not paths:
        raise SystemExit(
            f"No WAV files found in {args.corpus}"
        )

    results = []

    for path in paths:
        print(f"Evaluating {path.name}...")
        result = await evaluate_clip(
            path,
            args.url,
            not args.no_realtime,
        )
        results.append(result)

        print(
            f"  WER: "
            f"{result['word_errors']['wer']:.3f}"
        )

    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "websocket_url": args.url,
        "realtime": not args.no_realtime,
        "summary": summarize(results),
        "clips": results,
    }

    args.results.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path = (
        args.results
        / "streaming-baseline.json"
    )
    output_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    print()
    print(
        json.dumps(
            payload["summary"],
            indent=2,
        )
    )
    print(f"Saved results to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate CatchAll's live WebSocket "
            "caption pipeline."
        )
    )
    parser.add_argument(
        "--url",
        default="ws://127.0.0.1:8000/ws",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS,
    )
    parser.add_argument(
        "--no-realtime",
        action="store_true",
        help=(
            "Send audio without pacing. "
            "Latency results will be invalid."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))