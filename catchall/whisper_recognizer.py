from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from catchall.recognition import RecognitionHypothesis, TimedWord
from catchall.recognition_window import SAMPLE_RATE


class WhisperRecognizer:
    def __init__(
            self,
            model_name: str = "tiny.en",
            device: str = "cpu",
            compute_type: str = "int8",
            model: Any | None = None,
    ) -> None:
        if model is None:
            from faster_whisper import WhisperModel

            model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
            )

        self._model = model

    def transcribe(self, samples: Sequence[float]) -> RecognitionHypothesis:
        audio = np.asarray(samples, dtype=np.float32)

        segments, _= self._model.transcribe(
            audio,
            language="en",
            beam_size=1,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=False,
            word_timestamps = True
        )

        words: list[TimedWord] = []

        for segment in segments:
            for word in segment.words or ():
                text = word.word.strip()

                if not text:
                    continue

                words.append(TimedWord(
                    text=text,
                    start_sample=int(word.start * SAMPLE_RATE),
                    end_sample=int(word.end * SAMPLE_RATE),
                ))

        return RecognitionHypothesis(words=tuple(words))
