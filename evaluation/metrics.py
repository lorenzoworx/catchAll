from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Protocol

WORD_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")

class TimestampedWord(Protocol):
    text: str
    start_sample: int
    end_sample: int

@dataclass(frozen=True)
class WordErrors:
    substitutions: int
    deletions: int
    insertions: int
    reference_words: int

    @property
    def total(self) -> int:
        return(self.substitutions + self.deletions + self.insertions)

    @property
    def rate(self) -> float:
        if self.reference_words == 0:
            raise ValueError("word error rate requires reference words")

        return self.total / self.reference_words

def normalize_words(text: str) -> tuple[str, ...]:
    normalized = text.casefold().replace("’", "'")

    return tuple(WORD_PATTERN.findall(normalized))

def word_errors(reference: str, hypothesis: str) -> WordErrors:
    reference_words = normalize_words(reference)
    hypothesis_words = normalize_words(hypothesis)

    if not reference_words:
        raise ValueError("refernce transcript must contain words")

    rows = len(reference_words) + 1
    columns = len(hypothesis_words) + 1

    distances = [[0] * columns for _ in range(rows)]

    for row in range(rows):
        distances[row][0] = row

    for column in range(columns):
        distances[0][column] = column

    for row in range(1, rows):
        for column in range(1, columns):
            if (reference_words[row - 1] == hypothesis_words[column - 1]):
                substitution_cost = 0
            else:
                substitution_cost = 1

            distances[row][column] = min(
                distances[row - 1][column] + 1,
                distances[row][column - 1] + 1,
                distances[row - 1][column - 1]
                + substitution_cost,
            )

    substitutions = 0
    deletions = 0
    insertions = 0
    row = len(reference_words)
    column = len(hypothesis_words)

    while row > 0 or column > 0:
        if (row > 0 and column > 0 and reference_words[row - 1] == hypothesis_words[column - 1]):
            row -= 1
            column -= 1
            continue

        if (row > 0 and column > 0 and distances[row][column] == distances[row - 1][column - 1] + 1): 
            substitutions += 1
            row -= 1
            column -= 1
            continue

        if (row > 0 and distances[row][column] == distances[row - 1][column] + 1):
            deletions += 1
            row -= 1
            continue

        insertions += 1
        column -= 1

    return WordErrors(
        substitutions=substitutions,
        deletions=deletions,
        insertions=insertions,
        reference_words=len(reference_words)
    )

def percentile(values: Sequence[float], percentile_value: float,) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")

    if not 0 <= percentile_value <= 100:
        raise ValueError("percentile must be between zero and one hundred")

    ordered = sorted(values)
    rank = math.ceil(percentile_value / 100 * len(ordered))
    index = max(0, rank - 1)

    return ordered[index]

def count_overlapping_duplicates(words: Sequence[TimestampedWord]) -> int:
    duplicates = 0

    for previous, current in pairwise(words):
        previous_text = normalize_words(previous.text)
        current_text = normalize_words(current.text)

        if (previous_text and previous_text == current_text and current.start_sample < previous.end_sample):
            duplicates += 1

    return duplicates