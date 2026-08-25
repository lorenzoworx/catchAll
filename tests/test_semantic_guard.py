import pytest

from catchall.rewrite_guard import CompositeGuard, FaithfulnessGuard, SemanticSimilarityGuard


class FixedScorer:
    def __init__(self, similarity: float) -> None:
        self.similarity = similarity
        self.calls = 0

    def score(self, original: str, candidate: str) -> float:
        self.calls += 1
        return self.similarity

class BrokenScorer:
    def score(self, original: str, candidate: str) -> float:
        raise RuntimeError("similarity model failed")

def test_accepts_candidate_above_similarity_threshold() -> None:
    guard = SemanticSimilarityGuard(scorer=FixedScorer(0.86), minimum_similarity=0.80)

    assert guard.accepts(
        "The meeting begins at noon.",
        "The meeting starts at noon.",
    ) is True

def test_rejects_candidate_below_similarity_threshold() -> None:
    guard = SemanticSimilarityGuard(scorer=FixedScorer(0.61), minimum_similarity=0.80)

    assert guard.accepts(
            "The meeting begins at noon.",
            "The appointment was cancelled.",
        ) is False

def test_rejects_non_finite_similarity() -> None:
    guard = SemanticSimilarityGuard(scorer=FixedScorer(float("nan")))

    assert guard.accepts("Original.", "Candidate.") is False

def test_similarity_failure_is_fail_closed() -> None:
    guard = SemanticSimilarityGuard(scorer=BrokenScorer())

    assert guard.accepts("Original.", "Candidate.") is False

def test_rejects_invalid_similarity_threshold() -> None:
    with pytest.raises(ValueError,match="between zero and one"):
        SemanticSimilarityGuard(scorer=FixedScorer(0.9), minimum_similarity=1.1)

def test_composite_guard_requires_every_check_to_pass() -> None:
    scorer = FixedScorer(0.91)
    guard = CompositeGuard(FaithfulnessGuard(), SemanticSimilarityGuard(scorer))

    assert guard.accepts(
        "Dr. Steven Archer will not pay $200.",
        "Dr. Steven Archer won't make the $200 payment.",
    ) is True

    assert scorer.calls == 1

def test_detail_failure_skips_semantic_scoring() -> None:
    scorer = FixedScorer(0.99)
    guard = CompositeGuard(FaithfulnessGuard(), SemanticSimilarityGuard(scorer))

    assert guard.accepts(
        "The balance is $100.",
        "The balance is $900."
    ) is False

    assert scorer.calls == 0