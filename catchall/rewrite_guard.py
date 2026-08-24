from __future__ import annotations

import re
from collections import Counter

NUMBER_PATTERN = re.compile(
    r"(?<!\w)[$£€]?[+-]?\d+(?:,\d{3})*(?:\.\d+)?"
    r"(?:%|st|nd|rd|th)?(?!\w)"
)

NUMERIC_DATE_PATTERN = re.compile(r"(?<!\d)\d{1,4}[/-]\d{1,2}(?:[/-]\d{1,4})?(?!\d)")

WORD_PATTERN = re.compile(r"\b[A-Za-z]+(?:['’][A-Za-z]+)?\b")

NEGATION_PATTERN = re.compile(
    r"\b(?:no|not|never|none|nobody|nothing|neither|nor|"
    r"nowhere|cannot)\b|\b[A-Za-z]+n['’]t\b",
    re.IGNORECASE,
)

CAPITALIZED_PATTERN = re.compile(r"\b(?:[A-Z][a-z]+(?:['’-][A-Za-z]+)?|[A-Z]{2,})\b")

NAME_SEQUENCE_PATTERN = re.compile(
    r"\b[A-Z][a-z]+(?:['’-][A-Za-z]+)?"
    r"(?:\s+[A-Z][a-z]+(?:['’-][A-Za-z]+)?)+\b"
)

TITLED_NAME_PATTERN = re.compile(
    r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof)\.\s+"
    r"([A-Z][A-Za-z'’-]+)"
)

DATE_WORDS = {
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "today",
    "tomorrow",
    "yesterday",
    "tonight",
}

def extract_numbers(text: str) -> Counter[str]:
    return Counter(NUMBER_PATTERN.findall(text))

def extract_dates(text: str) -> Counter[str]:
    dates = [match.group(0).casefold() for match in NUMERIC_DATE_PATTERN.finditer(text)]

    dates.extend(word.casefold() for word in WORD_PATTERN.findall(text) if word.casefold() in DATE_WORDS)

    return Counter(dates)

def extract_negations(text: str) -> Counter[str]:
    negations = []

    for match in NEGATION_PATTERN.finditer(text):
        token = match.group(0).replace("’", "'").casefold()

        if token == "cannot" or token.endswith("n't"):
            token = "not"

        negations.append(token)

    return Counter(negations)

def _is_sentence_start(text: str, word_start: int) -> bool:
    prefix = text[:word_start].rstrip()

    return not prefix or prefix[-1] in ".!?"

def extract_names(text: str) -> Counter[str]:
    names: list[str] = []
    occupied_ranges: list[tuple[int, int]] = []

    for match in NAME_SEQUENCE_PATTERN.finditer(text):
        names.append(match.group(0).casefold())
        occupied_ranges.append(match.span())

    for match in TITLED_NAME_PATTERN.finditer(text):
        names.append(match.group(1).casefold())
        occupied_ranges.append(match.span(1))

    for match in CAPITALIZED_PATTERN.finditer(text):
        start, end = match.span()

        if any(occupied_start <= start and end <= occupied_end for occupied_start, occupied_end in occupied_ranges):
            continue

        token = match.group(0)

        if token.isupper() or not _is_sentence_start(text, start):
            names.append(token.casefold())

    return Counter(names)

class FaithfulnessGuard:
    def accepts(self, original: str, candidate: str) -> bool:
        return(
            extract_numbers(original) == extract_numbers(candidate)
            and extract_dates(original) == extract_dates(candidate)
            and extract_names(original) == extract_names(candidate)
            and extract_negations(original) == extract_negations(candidate)
        )