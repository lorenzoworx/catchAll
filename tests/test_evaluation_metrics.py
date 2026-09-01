from dataclasses import dataclass

import pytest

from evaluation.metrics import (
    count_overlapping_duplicates,
    normalize_words,
    percentile,
    word_errors,
)


@dataclass(frozen=True)
class Word:
    text: str
    start_sample: int
    end_sample: int


def test_normalizes_case_and_punctuation() -> None:
    assert normalize_words(
        "Hello, WORLD! Don’t stop."
    ) == (
        "hello",
        "world",
        "don't",
        "stop",
    )


def test_perfect_transcript_has_zero_wer() -> None:
    result = word_errors(
        "The meeting starts now.",
        "the meeting starts now",
    )

    assert result.total == 0
    assert result.rate == 0.0


def test_counts_word_error_operations() -> None:
    result = word_errors(
        "the cat sat down",
        "the dog sat here now",
    )

    assert result.substitutions == 2
    assert result.deletions == 0
    assert result.insertions == 1
    assert result.reference_words == 4
    assert result.rate == pytest.approx(0.75)


def test_counts_deleted_words() -> None:
    result = word_errors(
        "please send the form today",
        "please send today",
    )

    assert result.deletions == 2
    assert result.rate == pytest.approx(0.4)


def test_rejects_empty_reference() -> None:
    with pytest.raises(
        ValueError,
        match="must contain words",
    ):
        word_errors("", "some hypothesis")


def test_calculates_nearest_rank_percentile() -> None:
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 50) == 20.0
    assert percentile(values, 90) == 40.0


def test_detects_overlapping_duplicate_word() -> None:
    words = [
        Word("hello", 0, 100),
        Word("hello", 80, 180),
        Word("world", 180, 280),
    ]

    assert count_overlapping_duplicates(words) == 1


def test_allows_intentional_non_overlapping_repeat() -> None:
    words = [
        Word("hello", 0, 100),
        Word("hello", 120, 220),
    ]

    assert count_overlapping_duplicates(words) == 0