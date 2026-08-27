import numpy as np
import pytest

from catchall.nli import DEFAULT_NLI_MODEL_NAME, BidirectionalNliScorer


class FakeNliModel:
    def __init__(self) -> None:
        self.calls = []

    def predict(
        self, sentence_pairs: list[tuple[str, str]], *, show_progress_bar: bool
    ) -> np.ndarray:
        self.calls.append(
            {"sentence_pairs": sentence_pairs, "show_progress_bar": show_progress_bar}
        )

        return np.array([[0.0, 3.0, 0.0], [0.0, 2.0, 1.0]])


def test_scores_both_entailment_direction() -> None:
    model = FakeNliModel()
    scorer = BidirectionalNliScorer(model_factory=lambda model_name: model)
    result = scorer.score("The meeting begins.", "The meeting starts.")

    assert result.original_to_candidate.entailment == pytest.approx(0.909443)
    assert result.candidate_to_original.entailment == pytest.approx(0.665241)
    assert model.calls == [
        {
            "sentence_pairs": [
                ("The meeting begins.", "The meeting starts."),
                ("The meeting starts.", "The meeting begins."),
            ],
            "show_progress_bar": False,
        }
    ]


def test_model_is_loaded_lazily_and_once() -> None:
    model = FakeNliModel()
    requested_models = []

    def model_factory(model_name: str) -> FakeNliModel:
        requested_models.append(model_name)
        return model

    scorer = BidirectionalNliScorer(model_factory=model_factory)

    assert requested_models == []

    scorer.score("First.", "First.")
    scorer.score("Second.", "Second.")

    assert requested_models == [DEFAULT_NLI_MODEL_NAME]
    assert len(model.calls) == 2


def test_custom_model_name_is_used() -> None:
    model = FakeNliModel()
    requested_models = []

    def model_factory(model_name: str) -> FakeNliModel:
        requested_models.append(model_name)
        return model

    scorer = BidirectionalNliScorer(model_name="example/nli-model", model_factory=model_factory)

    scorer.score("Original.", "Candidate.")

    assert requested_models == ["example/nli-model"]


def test_rejects_incorrect_output_shape() -> None:
    class IncorrectShapeModel:
        def predict(
            self, sentence_pairs: list[tuple[str, str]], *, show_progress_bar: bool
        ) -> np.ndarray:
            return np.array([[0.0, 1.0, 0.0]])

    scorer = BidirectionalNliScorer(model_factory=lambda model_name: IncorrectShapeModel())

    with pytest.raises(ValueError, match="2 by 3"):
        scorer.score("Original.", "Candidate.")


def test_rejects_non_finite_scores() -> None:
    class NonFiniteModel:
        def predict(
            self, sentence_pairs: list[tuple[str, str]], *, show_progress_bar: bool
        ) -> np.ndarray:
            return np.array([[0.0, float("nan"), 0.0], [0.0, 1.0, 0.0]])

    scorer = BidirectionalNliScorer(model_factory=lambda model_name: NonFiniteModel())

    with pytest.raises(ValueError, match="non-finite"):
        scorer.score("Original.", "Candidate.")
