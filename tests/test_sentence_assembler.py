from catchall.recognition import TimedWord
from catchall.sentence_assembler import SentenceAssembler, ends_sentence


def word(text: str, start_sample: int, end_sample: int) -> TimedWord:
    return TimedWord(text=text, start_sample=start_sample, end_sample=end_sample)

def test_recognizes_sentence_punctuation() -> None:
    assert ends_sentence("Hello.") is True
    assert ends_sentence("Really?") is True
    assert ends_sentence("Stop!") is True
    assert ends_sentence('Ready?"') is True
    assert ends_sentence("continuing") is False


def test_waits_for_sentence_ending() -> None:
    assembler = SentenceAssembler()

    completed = assembler.add((
        word("Hello", 0, 100),
        word("there", 100, 200),
    ))

    assert completed == ()
    assert len(assembler.pending_words) == 2


def test_assembles_across_committed_batches() -> None:
    assembler = SentenceAssembler()

    assert assembler.add((word("Hello", 0, 100),)) == ()

    completed = assembler.add((
        word("there.", 100, 200),
        word("How", 200, 300),
    ))

    assert len(completed) == 1
    assert completed[0].text == "Hello there."
    assert completed[0].start_sample == 0
    assert completed[0].end_sample == 200

    assert tuple(item.text for item in assembler.pending_words) == ("How",)


def test_emits_multiple_sentences_from_one_batch() -> None:
    assembler = SentenceAssembler()

    completed = assembler.add((
        word("Hello.", 0, 100),
        word("How", 100, 200),
        word("are", 200, 300),
        word("you?", 300, 400),
    ))

    assert tuple(sentence.text for sentence in completed) == ("Hello.", "How are you?",)


def test_flush_returns_incomplete_sentence() -> None:
    assembler = SentenceAssembler()

    assembler.add((
        word("No", 0, 100),
        word("punctuation", 100, 200),
    ))
    
    sentence = assembler.flush()

    assert sentence is not None
    assert sentence.text == "No punctuation"
    assert assembler.pending_words == ()


def test_flush_on_empty_assembler_is_safe() -> None:
    assembler = SentenceAssembler()

    assert assembler.flush() is None