from catchall.plain_language import RuleBasedSimplifier


def test_replaces_complex_words_and_phrases() -> None:
    simplifier = RuleBasedSimplifier()

    result = simplifier.simplify("We require additional assistance at this point in time.")

    assert result == "We need more help now."

def test_preserves_initial_capitalization() -> None:
    simplifier = RuleBasedSimplifier()

    assert simplifier.simplify("Approximately five minutes remain.") == "About five minutes remain."

def test_preserves_all_capitalization() -> None:
    simplifier = RuleBasedSimplifier()

    assert simplifier.simplify("UTILIZE the microphone.") == "USE the microphone."

def test_does_not_replace_part_of_larger_word() -> None:
    simplifier = RuleBasedSimplifier()

    assert simplifier.simplify("The requirement is clear.") == "The requirement is clear."

def test_leaves_already_plain_sentence_unchanged() -> None:
    simplifier = RuleBasedSimplifier()

    sentence = "Please send the form today."

    assert simplifier.simplify(sentence) == sentence

def test_preserves_protected_details() -> None:
    simplifier = RuleBasedSimplifier()

    result = simplifier.simplify("Dr. Steven Archer requires $2,000 by Friday.")

    assert result == "Dr. Steven Archer needs $2,000 by Friday."

def test_preserves_negation() -> None:
    simplifier = RuleBasedSimplifier()

    result = simplifier.simplify("You must not utilize that microphone.")

    assert result == "You must not use that microphone."

