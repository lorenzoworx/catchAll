import numpy as np
import pytest

from catchall.semantic_similarity import DEFAULT_MODEL_NAME, SentenceTransformerSimilarityScorer


class FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def encode(self, sentences: list[str], *, normalize_embeddings: bool, convert_to_numpy: bool, show_progress_bar: bool) -> np.ndarray:
        self.calls.append({
            "sentences": sentences,
            "normalize_embeddings": (normalize_embeddings),
            "convert_to_numpy": convert_to_numpy,
            "show_progress_bar": show_progress_bar
        })

        return np.array([
            [1.0, 0.0],
            [0.8, 0.6]
        ])

def test_calculates_dot_product_of_normalized_embeddings() -> None:
    model = FakeModel()
    scorer = SentenceTransformerSimilarityScorer(model_factory=lambda model_name: model)

    similarity = scorer.score(
        "The meeting begins.",
        "The meeting starts."
    )

    assert similarity == pytest.approx(0.8)
    assert model.calls == [{
        "sentences": ["The meeting begins.", "The meeting starts."],
        "normalize_embeddings": True,
        "convert_to_numpy": True,
        "show_progress_bar": False,
    }]

def test_model_is_loaded_lazily_and_only_once() -> None:
    model = FakeModel()
    requested_models = []

    def model_factory(model_name: str) -> FakeModel:
        requested_models.append(model_name)
        return model

    scorer = SentenceTransformerSimilarityScorer(model_factory=model_factory)

    assert requested_models == []

    scorer.score("First.", "First")
    scorer.score("Second.", "Second.")

    assert requested_models == [DEFAULT_MODEL_NAME]
    assert len(model.calls) == 2

def test_custom_model_name_is_passed_to_factory() -> None:
    model = FakeModel()
    requested_models = []

    def model_factory(model_name: str) -> FakeModel:
        requested_models.append(model_name)
        return model

    scorer = SentenceTransformerSimilarityScorer(
        model_name="example/custom-model",
        model_factory=model_factory
    )

    scorer.score("Original.", "Candidate.")

    assert requested_models == ["example/custom-model"]

def test_rejects_invalid_embedding_count() -> None:
    class BrokenModel:
        def encode(self, sentences: list[str], **kwargs: object) -> np.ndarray:
            return np.array([[1.0, 0.0]])

    scorer = SentenceTransformerSimilarityScorer(model_factory=lambda model_name: BrokenModel())

    with pytest.raises(ValueError, match="must return two vectors"):
        scorer.score("Original.", "Candidate.")