import asyncio
import json
import struct
import wave
from pathlib import Path

import pytest

from evaluation.run_streaming import (
    FRAME_SAMPLES,
    StreamState,
    count_duplicate_boundaries,
    load_pcm16_mono,
    request_capture_finalization,
    summarize,
    trim_trailing_silence,
)


def write_wav(path: Path, *, sample_rate: int = 16_000, channels: int = 1, sample_width: int = 2) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(sample_width)
        audio.setframerate(sample_rate)
        audio.writeframes(
            b"\x00\x00" * FRAME_SAMPLES
        )


def test_loads_expected_wav_format(tmp_path: Path) -> None:
    path = tmp_path / "clip.wav"
    write_wav(path)

    pcm = load_pcm16_mono(path)

    assert len(pcm) == FRAME_SAMPLES * 2


def test_trims_silent_frames_after_the_last_active_frame() -> None:
    active = [1_000] * (FRAME_SAMPLES * 2)
    silence = [0] * (FRAME_SAMPLES * 3)
    pcm = struct.pack(f"<{len(active) + len(silence)}h", *(active + silence))

    trimmed, trimmed_samples = trim_trailing_silence(pcm)

    assert trimmed == struct.pack(f"<{len(active)}h", *active)
    assert trimmed_samples == len(silence)


def test_preserves_an_all_silent_clip() -> None:
    silence = [0] * FRAME_SAMPLES
    pcm = struct.pack(f"<{len(silence)}h", *silence)

    assert trim_trailing_silence(pcm) == (pcm, 0)


@pytest.mark.parametrize(
    ("threshold", "frame_samples"),
    [(-0.1, FRAME_SAMPLES), (0.01, 0)],
)
def test_rejects_invalid_silence_trimming_configuration(
    threshold: float,
    frame_samples: int,
) -> None:
    with pytest.raises(ValueError):
        trim_trailing_silence(
            b"\x00\x00",
            threshold=threshold,
            frame_samples=frame_samples,
        )


@pytest.mark.parametrize(
    ("sample_rate", "channels", "sample_width"),
    [
        (44_100, 1, 2),
        (16_000, 2, 2),
        (16_000, 1, 1),
    ],
)
def test_rejects_incorrect_wav_format(tmp_path: Path, sample_rate: int, channels: int, sample_width: int) -> None:
    path = tmp_path / "clip.wav"
    write_wav(
        path,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
    )

    with pytest.raises(ValueError):
        load_pcm16_mono(path)


def test_detects_duplicate_commit_boundary() -> None:
    committed = [
        {
            "text": "Hello world",
            "start_sample": 0,
            "end_sample": 200,
        },
        {
            "text": "world again",
            "start_sample": 180,
            "end_sample": 300,
        },
    ]

    assert count_duplicate_boundaries(committed) == 1


def test_allows_non_overlapping_repeat() -> None:
    committed = [
        {
            "text": "Hello world",
            "start_sample": 0,
            "end_sample": 200,
        },
        {
            "text": "world again",
            "start_sample": 220,
            "end_sample": 300,
        },
    ]

    assert count_duplicate_boundaries(committed) == 0


def test_requests_capture_finalization_and_measures_acknowledgment() -> None:
    class AcknowledgingWebSocket:
        def __init__(self, state: StreamState) -> None:
            self.state = state
            self.messages: list[dict[str, str]] = []

        async def send(self, raw_message: str) -> None:
            self.messages.append(json.loads(raw_message))
            assert self.state.capture_ended_at is not None
            self.state.capture_finalized_at = self.state.capture_ended_at + 0.25
            self.state.capture_finalized.set()

    async def scenario() -> None:
        state = StreamState()
        websocket = AcknowledgingWebSocket(state)

        latency = await request_capture_finalization(
            websocket,
            state,
            timeout=1,
        )

        assert websocket.messages == [{"type": "capture_end"}]
        assert latency == pytest.approx(250)

    asyncio.run(scenario())


def test_summary_includes_capture_finalization_latency() -> None:
    results = [
        {
            "word_errors": {
                "substitutions": 1,
                "deletions": 0,
                "insertions": 0,
                "reference_words": 10,
            },
            "commit_latencies_ms": [100.0],
            "recognition_lags_samples": [1_600],
            "capture_finalize_latency_ms": 250.0,
            "duplicate_boundaries": 0,
            "server_stats": {},
        },
        {
            "word_errors": {
                "substitutions": 0,
                "deletions": 1,
                "insertions": 0,
                "reference_words": 10,
            },
            "commit_latencies_ms": [200.0],
            "recognition_lags_samples": [3_200],
            "capture_finalize_latency_ms": 400.0,
            "duplicate_boundaries": 0,
            "server_stats": {},
        },
    ]

    summary = summarize(results)

    assert summary["corpus_wer"] == 0.1
    assert summary["capture_finalize_latency_p50_ms"] == 250.0
    assert summary["capture_finalize_latency_p90_ms"] == 400.0
