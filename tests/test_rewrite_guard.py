from catchall.rewrite_guard import (
    ContrastGuard,
    FaithfulnessGuard,
    extract_dates,
    extract_names,
    extract_negations,
    extract_numbers,
)


def test_extracts_protected_details() -> None:
    text = (
        "Dr. Steven Archer will not pay $2,000 "
        "on August 14."
    )

    assert extract_numbers(text) == {
        "$2,000": 1,
        "14": 1,
    }
    assert extract_dates(text) == {
        "august": 1,
    }
    assert extract_negations(text) == {
        "not": 1
    }
    assert "steven archer" in extract_names(text)

def test_accepts_rewrite_that_preserves_details() -> None:
    guard = FaithfulnessGuard()

    original = (
        "Dr. Steven Archer will not pay $2,000 "
        "on August 14."
    )
    candidate = (
        "Dr. Steven Archer won't make the $2,000 payment "
        "on August 14."
    )

    assert guard.accepts(original, candidate) is True

def test_rejects_changed_number() -> None:
    guard = FaithfulnessGuard()

    assert guard.accepts(
        "The balance is $2,000",
        "The balance is $2,500",
    ) is False

def test_rejects_changed_date() -> None:
    guard = FaithfulnessGuard()

    assert guard.accepts(
        "The appointment is on August 14.",
        "The appointment is on August 13."
    ) is False
    

def test_rejects_changed_name() -> None:
    guard = FaithfulnessGuard()

    assert guard.accepts(
        "Please contact Steven Archer.",
        "Please contact Saul Archer."
    ) is False
    

def test_rejects_removed_negation() -> None:
    guard = FaithfulnessGuard()

    assert guard.accepts(
        "The service is not available.",
        "The service is available."
    ) is False
    

def test_rejects_added_negation() -> None:
    guard = FaithfulnessGuard()

    assert guard.accepts(
        "The service is available.",
        "The service is not available."
    ) is False
    

def test_allows_text_without_changed_protected_details() -> None:
    guard = FaithfulnessGuard()

    assert guard.accepts(
        "People need captions that are easy to read.",
        "Clear captions help people understand",
    ) is True
    
def test_rejects_explicit_start_stop_reversal() -> None:
    guard = ContrastGuard()

    assert guard.accepts("The blue button starts recording.", "The blue button stops recording.") is False

def test_accepts_synonyms_on_same_contrast_side() -> None:
    guard = ContrastGuard()

    assert guard.accepts("The meeting begins at noon.", "The meeting starts at noon.") is True

def test_rejects_before_after_reversal() -> None:
    guard = ContrastGuard()

    assert guard.accepts("The meeting begins before lunch.", "The meeting begins after lunch.") is False

def test_rejects_storage_deletion_reversal() -> None:
    guard = ContrastGuard()

    assert guard.accepts("Captions are deleted after the session.", "Captions are stored after the session") is False

def test_allows_contrast_term_to_be_rephrased() -> None:
    guard = ContrastGuard()

    assert guard.accepts("Submit the form before Friday.", "Send in the form by Friday.") is True

def test_allows_sentence_containing_both_sides() -> None:
    guard = ContrastGuard()

    sentence = "You can start and stop recording."

    assert guard.accepts(sentence, sentence) is True
