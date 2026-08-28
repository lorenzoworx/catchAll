from __future__ import annotations

import re

DEFAULT_REPLACEMENTS = (
    ("due to the fact that", "because"),
    ("at this point in time", "now"),
    ("a large number of", "many"),
    ("in order to", "to"),
    ("subsequent to", "after"),
    ("prior to", "before"),
    ("approximately", "about"),
    ("additional", "more"),
    ("assistance", "help"),
    ("commences", "starts"),
    ("commence", "start"),
    ("terminates", "ends"),
    ("terminate", "end"),
    ("utilizes", "uses"),
    ("utilize", "use"),
    ("requires", "needs"),
    ("require", "need"),
    ("purchase", "buy"),
)

class RuleBasedSimplifier:
    def __init__(self, replacements: tuple[tuple[str, str], ...,] = DEFAULT_REPLACEMENTS) -> None:
        self._rules = tuple((
            re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE),
            replacement,
        ) for source, replacement in replacements)

    def simplify(self, text: str) -> str:
        rewritten = text

        for pattern, replacement in self._rules:
            rewritten = pattern.sub(
                lambda match, replacement=replacement: (
                    self._match_case(
                        match.group(0),
                        replacement,
                    )
                ),
                rewritten,
            )

        return rewritten

    @staticmethod
    def _match_case(original: str, replacement: str) -> str:
        if original.isupper():
            return replacement.upper()

        if original[0].isupper():
            return (replacement[0].upper() + replacement[1:])

        return replacement