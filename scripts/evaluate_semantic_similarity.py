from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from catchall.rewrite_guard import FaithfulnessGuard
from catchall.semantic_similarity import SentenceTransformerSimilarityScorer

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

def load_pairs() -> list[EvaluationPair]:
    raw_pairs = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return [
        EvaluationPair(
            identifier=item["id"],
            safe=item["safe"],
            original=item["original"],
            candidate=item["candidate"]
        ) for item in raw_pairs
    ]

def main() -> None:
    scorer = SentenceTransformerSimilarityScorer()
    detail_guard = FaithfulnessGuard()

    safe_scores: list[float] = []
    unsafe_scores: list[float] = []

    print(
        f"{'expected':<10}"
        f"{'details':<10}"
        f"{'score':>8} case"
    )

    for pair in load_pairs():
        score = scorer.score(pair.original, pair.candidate)
        details_pass = detail_guard.accepts(pair.original, pair.candidate)
        expected = "safe" if pair.safe else "unsafe"
        details = "pass" if details_pass else "reject"

        print(
            f"{expected:<10}"
            f"{details:<10}"
            f"{score:>8.4f} "
            f"{pair.identifier}"
        )

        if not details_pass:
            continue

        if pair.safe:
            safe_scores.append(score)
        else:
            unsafe_scores.append(score)

    print()

    if not safe_scores or not unsafe_scores:
        print(
            "Not enough detail-guard-passing examples "
            "to evaluate a semantic threshold."
        )
        return

    lowest_safe = min(safe_scores)
    highest_unsafe = max(unsafe_scores)

    print(f"Lowest safe score: {lowest_safe:.4f}")
    print(f"Highest unsafe score: {highest_unsafe:.4f}")

    if highest_unsafe < lowest_safe:
        midpoint = (highest_unsafe + lowest_safe) / 2
        print("The sample has a clean separation.")
        print(
            "Possible starting threshold: "
            f"{midpoint:.4f}"
        )
    else:
        print("There is no clean threshold for this sample.")
        print(
            "Embedding similarity alone cannot enforce "
            "the meaning-preservation requirement."
        )


if __name__ == "__main__":
    main()