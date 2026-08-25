from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

DEFAULT_MODEL_NAME = ("sentence-transformers/all-MiniLM-L6-v2")

class EmbeddingModel(Protocol):
    def encode(self, sentences: list[str], *, nomralize_embeddings: bool, convert_to_numpy: bool, show_progress_bar: bool) -> Any:
        """Encode sentences as vectors"""

ModelFactory = Callable[[str], EmbeddingModel]

def load_sentence_transformer(model_name: str) -> EmbeddingModel:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError("Install Catchall with the simplification extra") from error

    return SentenceTransformer(model_name)

class SentenceTransformerSimilarityScorer:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, model_factory: ModelFactory = load_sentence_transformer) -> None:
        self.model_name = model_name
        self._model_factory = model_factory
        self._model: EmbeddingModel | None = None

    def score(self, original: str, candidate: str) -> float:
        model = self._get_model()

        embeddings = model.encode(
            [original, candidate],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        if len(embeddings) != 2:
            raise ValueError("embedding model must return two vectors")

        return float(embeddings[0] @ embeddings[1])

    def _get_model(self) -> EmbeddingModel:
        if self._model is None:
            self._model = self._model_factory(self.model_name)

        return self._model