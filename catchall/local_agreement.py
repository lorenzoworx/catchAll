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

    @property
    def committed_word_count(self) -> int:
        return self._committed_word_count

    @property
    def committed_through_sample(self) -> int:
        return self._committed_through_sample

    def update(self, words: Sequence[TimedWord]) -> AgreementResult:
        current = tuple(word for word in words if (word.end_sample > self._committed_through_sample))

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

        self._committed_word_count += len(committed)
        self._committed_through_sample = max(self._committed_through_sample, committed[-1].end_sample)

        provisional = current[len(committed) :]
        self._previous = provisional

        return AgreementResult(committed=committed, provisional=provisional)
