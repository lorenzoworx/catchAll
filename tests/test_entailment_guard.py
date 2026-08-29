import pytest

from catchall.nli import BidirectionalNliResult, NliProbabilities
from catchall.rewrite_guard import (
    BidirectionalEntailmentGuard,
    CompositeGuard,
    ContrastGuard,
    FaithfulnessGuard,
)


class FixedNliScorer:
    def __init__(self, result: BidirectionalNliResult) -> None:
        self.result = result
        self.calls = 0

    def score(self, original: str, candidate: str) -> BidirectionalNliResult:
        self.calls += 1
        return self.result

class BrokenNliScorer:
    def score(self, original: str, candidate: str) -> BidirectionalNliResult:
        raise RuntimeError("NLI failed")

def result_with(*, forward_entailment: float, forward_contradiction: float, reverse_entailment: float, reverse_contradiction: float) -> BidirectionalNliResult:
    return BidirectionalNliResult(
        original_to_candidate=NliProbabilities(
            contradiction=forward_contradiction,
            entailment=forward_entailment,
            neutral=(1.0 - forward_entailment - forward_contradiction)
        ),
        candidate_to_original=NliProbabilities(
            contradiction=reverse_contradiction,
            entailment=reverse_entailment,
            neutral=(1.0 - reverse_entailment - reverse_contradiction)
        )
    )

def test_accepts_bidirectional_entailment() -> None:
    guard = BidirectionalEntailmentGuard(
        scorer=FixedNliScorer(
            result_with(
                forward_entailment=0.84,
                forward_contradiction=0.13,
                reverse_entailment=0.97,
                reverse_contradiction=0.01
            )
        )
    )

    assert guard.accepts("Submit the form before Friday.", "Send in the form by Friday.") is True

def test_rejects_low_forward_entailment() -> None:
    guard = BidirectionalEntailmentGuard(
        scorer=FixedNliScorer(
            result_with(
                forward_entailment=0.70,
                forward_contradiction=0.10,
                reverse_entailment=0.95,
                reverse_contradiction=0.02
            )
        )
    )

    assert guard.accepts("Original.", "Candidate.") is False

def test_rejects_low_reverse_entailment() -> None:
    guard = BidirectionalEntailmentGuard(
        scorer=FixedNliScorer(
            result_with(
                forward_entailment=0.95,
                forward_contradiction=0.01,
                reverse_entailment=0.70,
                reverse_contradiction=0.10
            )
        )
    )

    assert guard.accepts("Original.", "Candidate.") is False

def test_rejects_high_contradiction() -> None:
    guard = BidirectionalEntailmentGuard(
        scorer=FixedNliScorer(
            result_with(
                forward_entailment=0.85,
                forward_contradiction=0.25,
                reverse_entailment=0.90,
                reverse_contradiction=0.05,
            )
        )
    )

    assert guard.accepts("Original.", "Candidate.") is False

def test_nli_failure_is_fail_closed() -> None:
    guard = BidirectionalEntailmentGuard(scorer=BrokenNliScorer())

    assert guard.accepts("Original.", "Candidate.") is False

@pytest.mark.parametrize(
    ("minimum_entailment", "maximum_contradiction"),
    [
        (-0.1, 0.2),
        (1.1, 0.2),
        (0.8, -0.1),
        (0.8, 1.1)
    ],
)
def test_rejects_invalid_thresholds(minimum_entailment: float, maximum_contradiction: float) -> None:
    with pytest.raises(ValueError):
        BidirectionalEntailmentGuard(
            scorer=FixedNliScorer(
                result_with(
                    forward_entailment=0.9,
                    forward_contradiction=0.05,
                    reverse_entailment=0.9,
                    reverse_contradiction=0.05
                )
            ),
            minimum_entailment=minimum_entailment,
            maximum_contradiction=(maximum_contradiction)
        )

def test_detail_failure_skips_nli() -> None:
    scorer = FixedNliScorer(
        result_with(
            forward_entailment=0.99,
            forward_contradiction=0.00,
            reverse_entailment=0.99,
            reverse_contradiction=0.00
        )
    )
    guard = CompositeGuard(FaithfulnessGuard(), ContrastGuard(), BidirectionalEntailmentGuard(scorer))

    assert guard.accepts("The balance is $100.", "The balance is $900.") is False
    assert scorer.calls == 0

def test_contrast_failure_skips_nli() -> None:
    scorer = FixedNliScorer(
        result_with(
            forward_entailment=0.99,
            forward_contradiction=0.00,
            reverse_entailment=0.99,
            reverse_contradiction=0.00
        )
    )

    guard = CompositeGuard(FaithfulnessGuard(), ContrastGuard(), BidirectionalEntailmentGuard(scorer))

    assert guard.accepts("The blue button starts recording.", "The blue button stops recording.") is False
    assert scorer.calls == 0