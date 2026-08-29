from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol

import numpy as np

DEFAULT_NLI_MODEL_NAME = "cross-encoder/nli-deberta-v3-xsmall"


class NliModel(Protocol):
    def predict(self, sentence_pairs: list[tuple[str, str]], *, show_progress_bar: bool) -> Any:
        """Return NLI logits for each sentence pair."""


NliModelFactory = Callable[[str], NliModel]


def load_nli_model(model_name: str) -> NliModel:
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as error:
        raise RuntimeError("Install catchall with the simplification extra") from error

    return CrossEncoder(model_name)


@dataclass(frozen=True)
class NliProbabilities:
    contradiction: float
    entailment: float
    neutral: float


@dataclass(frozen=True)
class BidirectionalNliResult:
    original_to_candidate: NliProbabilities
    candidate_to_original: NliProbabilities


class BidirectionalNliScorer:
    def __init__(
        self,
        model_name: str = DEFAULT_NLI_MODEL_NAME,
        model_factory: NliModelFactory = load_nli_model,
    ) -> None:
        self.model_name = model_name
        self._model_factory = model_factory
        self._model: NliModel | None = None
        self._model_lock = Lock()
        self._prediction_lock = Lock()

    def score(self, original: str, candidate: str) -> BidirectionalNliResult:
        model = self._get_model()
        with self._prediction_lock:
            raw_logits = model.predict([(original, candidate), (candidate, original)], show_progress_bar=False)

            logits = np.asarray(raw_logits, dtype=float)

        if logits.shape != (2, 3):
            raise ValueError("NLI model must return a 2 by 3 score matrix")

        if not np.isfinite(logits).all():
            raise ValueError("NLI model returned non-finite scores")

        probabilities = self._softmax(logits)

        return BidirectionalNliResult(
            original_to_candidate=self._to_probabilities(probabilities[0]),
            candidate_to_original=self._to_probabilities(probabilities[1]),
        )

    def _get_model(self) -> NliModel:
        model = self._model

        if model is not None:
            return model

        with self._model_lock:
            if self._model is None:
                self._model = self._model_factory(self.model_name)

            return self._model

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - logits.max(axis=1, keepdims=True)
        exponentials = np.exp(shifted)

        return exponentials / exponentials.sum(axis=1, keepdims=True)

    @staticmethod
    def _to_probabilities(scores: np.ndarray) -> NliProbabilities:
        return NliProbabilities(
            contradiction=float(scores[0]),
            entailment=float(scores[1]),
            neutral=float(scores[2]),
        )
