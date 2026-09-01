from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

from catchall.recognition import TimedWord


def normalize_word(text: str) -> str:
    return "".join(character for character in text.casefold() if character.isalnum())

def longest_common_prefix(older: Sequence[TimedWord], newer: Sequence[TimedWord]) -> tuple[TimedWord, ...]:
    prefix: list[TimedWord] = []

    for older_word, newer_word in zip(older, newer, strict=False):
        older_normalized = normalize_word(older_word.text)
        newer_normalized = normalize_word(newer_word.text)

        if ((not older_normalized) or (older_normalized != newer_normalized)):
            break

        prefix.append(older_word)

    return tuple(prefix)

@dataclass(frozen=True)
class AgreementResult:
    committed: tuple[TimedWord, ...]
    provisional: tuple[TimedWord, ...]

class LocalAgreement:
    def __init__(self) -> None:
        self._previous: tuple[TimedWord, ...] = ()
        self._committed_through_sample = 0
        self._committed_word_count = 0
        self._committed_tail: deque[str] = deque(maxlen=8)

    @property
    def committed_word_count(self) -> int:
        return self._committed_word_count

    @property
    def committed_through_sample(self) -> int:
        return self._committed_through_sample

    def update(self, words: Sequence[TimedWord]) -> AgreementResult:
        current = tuple(word for word in words if(word.end_sample > self._committed_through_sample))

        current = self._strip_committed_overlap(current)

        if not self._previous:
            self._previous = current

            return AgreementResult(
                committed=(),
                provisional=current,
            )

        committed = longest_common_prefix(
            self._previous,
            current,
        )

        if not committed:
            self._previous = current

            return AgreementResult(
                committed=(),
                provisional=current,
            )

        self._record_committed(committed)

        provisional = current[len(committed) :]
        self._previous = provisional

        return AgreementResult(committed=committed, provisional=provisional)

    def _record_committed(self, words: Sequence[TimedWord]) -> None:
        if not words:
            return

        self._committed_word_count += len(words)
        self._committed_through_sample = max(self._committed_through_sample, words[-1].end_sample)
        self._committed_tail.extend(normalize_word(word.text) for word in words)

    def _strip_committed_overlap(self, words: tuple[TimedWord, ...]) -> tuple[TimedWord, ...]:
        if not words or not self._committed_tail:
            return words

        eligible_words = 0

        for word in words:
            if (word.start_sample < self._committed_through_sample):
                eligible_words += 1
            else:
                break

        committed_tail = tuple(self._committed_tail)
        maximum_overlap = min(eligible_words, len(committed_tail))

        for overlap in range(maximum_overlap, 0, -1):
            candidate = tuple(normalize_word(word.text) for word in words[:overlap])
            committed = committed_tail[-overlap:]

            if candidate == committed:
                return words[overlap:]

        return words
