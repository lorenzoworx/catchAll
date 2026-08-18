from dataclasses import dataclass
from typing import Any

import numpy as np

from catchall.whisper_recognizer import WhisperRecognizer


@dataclass
class FakeSegment:
    text: str

class FakeModel:
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
        self.audio: np.ndarray[Any, Any] | None = None
        self.options: dict[str, object] = {}

    def transcribe(self, audio: np.ndarray[Any, Any], **options: object) -> tuple[object, object]:
        self.audio = audio
        self.options = options

        segments = (
            FakeSegment(text)
            for text in self._texts
        )

        return segments, object()

def test_converts_audio_to_float32_and_joins_segments() -> None:
    model = FakeModel([
        " Hello ",
        " world. ",
    ])
    recognizer = WhisperRecognizer(model=model)

    result = recognizer.transcribe([0.0, 0.25, -0.25])

    assert result == "Hello world."
    assert model.audio is not None
    assert model.audio.dtype == np.float32
    assert model.audio.tolist() == [0.0, 0.25, -0.25]

def test_uses_low_latency_english_options() -> None:
    model = FakeModel(["test"])
    recognizer = WhisperRecognizer(model=model)

    recognizer.transcribe([0.0])

    assert model.options == {
        "language": "en",
        "beam_size": 1,
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "vad_filter": False,
    }

def test_ignores_empty_segments() -> None:
    model = FakeModel([
        " ",
        "",
    ])
    recognizer = WhisperRecognizer(model=model)

    assert recognizer.transcribe([0.0]) == ""