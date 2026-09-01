import wave
from pathlib import Path

import pytest

from evaluation.run_streaming import (
    FRAME_SAMPLES,
    count_duplicate_boundaries,
    load_pcm16_mono,
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