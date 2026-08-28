from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from catchall.nli import BidirectionalNliScorer
from catchall.rewrite_guard import CompositeGuard, ContrastGuard, FaithfulnessGuard

DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "semantic_pairs.json"
)

@dataclass(frozen=True)
class EvaluationPair:
    identifier: str
    safe: bool
    original: str
    candidate: str

@dataclass(frozen=True)
class EvaluationResult:
    safe: bool
    minimum_entailment: float
    maximum_contradiction: float

def load_pairs() -> list[EvaluationPair]:
    raw_pairs = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    pairs = []

    for item in raw_pairs:
        safe = item["safe"]

        if not isinstance(safe, bool):
            raise TypeError(f"{item['id']}: safe must be a JSON boolean")

        pairs.append(EvaluationPair(
            identifier=item["id"],
            safe=safe,
            original=item["original"],
            candidate=item["candidate"]
        ))

    return pairs

def main() -> None:
    scorer = BidirectionalNliScorer()
    pre_nli_guard = CompositeGuard(FaithfulnessGuard(), ContrastGuard())
    measurements: list[EvaluationResult] = []

    print(
        f"{'expected':<9}"
        f"{'details':<9}"
        f"{'o->c ent':>10}"
        f"{'o->c con':>10}"
        f"{'c->o ent':>10}"
        f"{'c->o con':>10}  case"
    )

    for pair in load_pairs():
        details_pass =  pre_nli_guard.accepts(pair.original, pair.candidate)
        result = scorer.score(pair.original, pair.candidate)

        forward = result.original_to_candidate
        reverse = result.candidate_to_original

        expected = "safe" if pair.safe else "unsafe"
        details = "pass" if details_pass else "reject"

        print(
            f"{expected:<9}"
            f"{details:<9}"
            f"{forward.entailment:>10.4f}"
            f"{forward.contradiction:>10.4f}"
            f"{reverse.entailment:>10.4f}"
            f"{reverse.contradiction:>10.4f}  "
            f"{pair.identifier}"
        )

        if not details_pass:
            continue

        measurements.append(EvaluationResult(
            safe=pair.safe,
            minimum_entailment=min(forward.entailment, reverse.entailment),
            maximum_contradiction=max(forward.contradiction, reverse.contradiction)
        ))

    safe_results = [result for result in measurements if result.safe]
    unsafe_results = [result for result in measurements if not result.safe]

    print()

    if not safe_results or not unsafe_results:
        print("Not enough examples passed the detail guard.")
        return

    lowest_safe_entailment = min(result.minimum_entailment for result in safe_results)
    highest_unsafe_entailment = max(result.minimum_entailment for result in unsafe_results)
    highest_safe_contradiction = max(result.maximum_contradiction for result in safe_results)
    lowest_unsafe_contradiction = min(result.maximum_contradiction for result in unsafe_results)

    print(f"Lowest safe minimum entailment: {lowest_safe_entailment:.4f}")
    print(f"Highest unsafe minimum entailment: {highest_unsafe_entailment:.4f}")
    print(f"Highest safe maximum contradiction: {highest_safe_contradiction:.4f}")
    print(f"Lowest unsafe maximum contradiction: {lowest_unsafe_contradiction:.4f}")


if __name__ == "__main__":
    main()