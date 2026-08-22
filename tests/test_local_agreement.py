from catchall.local_agreement import LocalAgreement, longest_common_prefix, normalize_word
from catchall.recognition import TimedWord


def word(text: str, start_sample: int, end_sample: int) -> TimedWord:
    return TimedWord(text=text, start_sample=start_sample, end_sample=end_sample)

def texts(words: tuple[TimedWord, ...]) -> list[str]:
    return [item.text for item in words]

def test_normalizes_case_and_punctuation() -> None:
    assert normalize_word("Hello!") == "hello"
    assert normalize_word('"World."') == "world"
    assert normalize_word("42") == "42"

def test_finds_matching_prefix() -> None:
    older = (
        word("Hello", 0, 100),
        word("World.", 100, 200),
    )
    newer = (
        word("hello", 0, 110),
        word("world", 110, 210),
        word("today", 210, 300),
    )

    prefix = longest_common_prefix(older, newer)

    assert texts(prefix) == ["Hello", "World."]

def test_stops_at_first_disagreement() -> None:
    older = (
        word("hello", 0, 100),
        word("world", 100, 200),
    )
    newer = (
        word("hello", 0, 100),
        word("there", 100, 200),
    )

    prefix = longest_common_prefix(older, newer)

    assert texts(prefix) == ["hello"]

def test_first_hypothesis_remains_provisional() -> None:
    agreement = LocalAgreement()
    hypothesis = (
        word("hello", 0, 100),
        word("world", 100, 200),
    )

    result = agreement.update(hypothesis)

    assert result.committed == ()
    assert result.provisional == hypothesis

def test_two_hypotheses_commit_shared_prefix() -> None:
    agreement = LocalAgreement()

    agreement.update(
        (
            word("hello", 0, 100),
            word("world", 100, 200),
        )
    )
    result = agreement.update(
        (
            word("hello", 0, 105),
            word("world", 105, 205),
            word("today", 205, 300),
        )
    )

    assert texts(result.committed) == [
        "hello",
        "world",
    ]
    assert texts(result.provisional) == ["today"]
    assert agreement.committed_word_count == 2
    assert agreement.committed_through_sample == 200

def test_disagreement_does_not_commit_first_word() -> None:
    agreement = LocalAgreement()

    agreement.update((
        word("alpha", 0, 100),
    ))

    result = agreement.update((
        word("beta", 0, 100),
    ))

    assert result.committed == ()
    assert texts(result.provisional) == ["beta"]

def test_committed_words_are_not_emitted() -> None:
    agreement = LocalAgreement()

    first = (
        word("hello", 0, 100),
        word("world", 100, 200),
    )

    agreement.update(first)
    result = agreement.update(first)

    assert texts(result.committed) == [
        "hello",
        "world",
    ]

    next_hypothesis = (
        word("hello", 0, 100),
        word("world", 100, 200),
        word("again", 200, 300),
    )

    result = agreement.update(next_hypothesis)

    assert result.committed == ()
    assert texts(result.provisional) == ["again"]

def test_new_words_commit_after_an_earlier_commit() -> None:
    agreement = LocalAgreement()

    agreement.update((
        word("hello", 0, 100),
        word("world", 100, 200),
    ))
    agreement.update((
        word("hello", 0, 100),
        word("world", 100, 200),
        word("today", 200, 300),
    ))

    result = agreement.update((
        word("hello", 0, 100),
        word("world", 100, 200),
        word("today", 200, 300),
        word("again", 300, 400),
    ))

    assert texts(result.committed) == ["today"]
    assert texts(result.provisional) == ["again"]

def test_redecoded_last_word_is_not_recommitted() -> None:
    agreement = LocalAgreement()

    original = (word("me?", 100, 200),)

    agreement.update(original)
    result = agreement.update(original)

    assert texts(result.committed) == ["me?"]

    # Whisper recognizes the same audio again, but its
    # timestamp has drifted later.
    repeated = (word("me?", 150, 230),)

    result = agreement.update(repeated)
    assert result.committed == ()
    assert result.provisional == ()

    result = agreement.update(repeated)
    assert result.committed == ()
    assert result.provisional == ()


def test_genuine_repeated_word_after_boundary_is_kept() -> None:
    agreement = LocalAgreement()

    original = (word("go", 0, 100),)

    agreement.update(original)
    agreement.update(original)

    # This repetition starts after the committed boundary,
    # so it represents genuinely new speech.
    repeated = (word("go", 110, 200),)

    result = agreement.update(repeated)
    assert texts(result.provisional) == ["go"]

    result = agreement.update(repeated)
    assert texts(result.committed) == ["go"]


def test_redecoded_committed_suffix_is_removed() -> None:
    agreement = LocalAgreement()

    original = (
        word("hello", 0, 100),
        word("me?", 100, 200),
    )

    agreement.update(original)
    agreement.update(original)

    result = agreement.update(
        (
            word("me?", 150, 230),
            word("today", 230, 300),
        )
    )

    assert result.committed == ()
    assert texts(result.provisional) == ["today"]