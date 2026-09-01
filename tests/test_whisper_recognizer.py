from dataclasses import dataclass
from typing import Any

import numpy as np

from catchall.recognition import TimedWord
from catchall.whisper_recognizer import WhisperRecognizer


@dataclass
class FakeWord:
    word: str
    start: float
    end: float

@dataclass
class FakeSegment:
    words: list[FakeWord] | None

class FakeModel:
    def __init__(self, segments: list[FakeSegment]) -> None:
        self._segments = segments
        self.audio: np.ndarray[Any, Any] | None = None
        self.options: dict[str, object] = {}

    def transcribe(self, audio: np.ndarray[Any, Any], **options: object) -> tuple[object, object]:
        self.audio = audio
        self.options = options

        return iter(self._segments), object()

def test_converts_audio_to_float32_and_joins_segments() -> None:
    model = FakeModel([
        FakeSegment(words=[
            FakeWord(" Hello", 0.1, 0.4),
            FakeWord(" world.", 0.4, 0.9),
        ])
    ])
    recognizer = WhisperRecognizer(model=model)

    samples = [0.0] * 16_000
    samples[1] = 0.25
    samples[2] = -0.25

    result = recognizer.transcribe(samples)

    assert result.words == (
        TimedWord(
            text="Hello",
            start_sample=1_600,
            end_sample=6_400,
        ),
        TimedWord(
            text="world.",
            start_sample=6_400,
            end_sample=14_400
        )
    )
    assert model.audio is not None
    assert model.audio.dtype == np.float32
    assert model.audio[:3].tolist() == [0.0, 0.25, -0.25]

def test_uses_low_latency_english_options() -> None:
    model = FakeModel([FakeSegment(
        words=[FakeWord(" test", 0.0, 0.1)]
    )])
    recognizer = WhisperRecognizer(model=model)

    recognizer.transcribe([0.0])

    assert model.options == {
        "language": "en",
        "beam_size": 1,
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "vad_filter": False,
        "word_timestamps": True,
    }

def test_ignores_empty_segments() -> None:
    model = FakeModel([
        FakeSegment(
            words=[FakeWord("   ", 0.0, 0.1)]
        ),
        FakeSegment(words=None),
        FakeSegment(words=[])
    ])
    recognizer = WhisperRecognizer(model=model)

    result = recognizer.transcribe([0.0])

    assert result.words == ()

def test_reports_recognizer_configuration() -> None:
    model = FakeModel([])

    recognizer = WhisperRecognizer(
        model_name="base.en",
        device="cpu",
        compute_type="int8",
        model=model,
    )

    assert recognizer.configuration == {
        "model_name": "base.en",
        "device": "cpu",
        "compute_type": "int8",
    }