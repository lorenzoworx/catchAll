from collections.abc import Sequence
from dataclasses import dataclass

from catchall.recognition import TimedWord

CLOSING_CHARACTERS = "\"'”’)]}"


def ends_sentence(text: str) -> bool:
    candidate = text.rstrip()

    while (candidate and candidate[-1] in CLOSING_CHARACTERS):
        candidate = candidate[:-1].rstrip()

    return candidate.endswith((".", "?", "!"))


@dataclass(frozen=True)
class CommittedSentence:
    words: tuple[TimedWord, ...]

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)

    @property
    def start_sample(self) -> int:
        return self.words[0].start_sample

    @property
    def end_sample(self) -> int:
        return self.words[-1].end_sample


class SentenceAssembler:
    def __init__(self) -> None:
        self._pending: list[TimedWord] = []

    @property
    def pending_words(self) -> tuple[TimedWord, ...]:
        return tuple(self._pending)

    def add(self, words: Sequence[TimedWord]) -> tuple[CommittedSentence, ...]:
        completed: list[CommittedSentence] = []

        for word in words:
            self._pending.append(word)

            if ends_sentence(word.text):
                completed.append(
                    CommittedSentence(
                        words=tuple(self._pending)
                    )
                )
                self._pending.clear()

        return tuple(completed)

    def flush(self) -> CommittedSentence | None:
        if not self._pending:
            return None

        sentence = CommittedSentence(words=tuple(self._pending))
        self._pending.clear()

        return sentence