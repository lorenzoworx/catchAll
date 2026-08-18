import pytest

from catchall.recognition_window import RecognitionWindowBuffer


def test_waits_for_minimum_audio() -> None:
    buffer = RecognitionWindowBuffer(
        min_samples=4,
        max_samples=8,
        hop_samples=2,
    )

    assert buffer.add([0.0, 1.0, 2.0]) == []

    windows = buffer.add([3.0])

    assert len(windows) == 1
    assert windows[0].start_sample == 0
    assert windows[0].end_sample == 4
    assert windows[0].samples == (0.0, 1.0, 2.0, 3.0)

def test_emits_overlapping_growing_windows() -> None:
    buffer = RecognitionWindowBuffer(
        min_samples=4,
        max_samples=8,
        hop_samples=2,
    )

    windows = buffer.add(range(6))

    assert len(windows) == 2

    assert windows[0].start_sample == 0
    assert windows[0].end_sample == 4
    assert windows[0].samples == (0.0, 1.0, 2.0, 3.0)

    assert windows[1].start_sample == 0
    assert windows[1].end_sample == 6
    assert windows[1].samples == (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)

def test_limits_history_and_tracks_absolute_position() -> None:
    buffer = RecognitionWindowBuffer(
        min_samples=4,
        max_samples=8,
        hop_samples=2,
    )

    windows = buffer.add(range(10))
    latest = windows[-1]

    assert latest.start_sample == 2
    assert latest.end_sample == 10
    assert latest.samples == (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0,)

def test_results_do_not_depend_on_input_chunk_boundaries() -> None:
    one_shot = RecognitionWindowBuffer(
        min_samples=4,
        max_samples=8,
        hop_samples=2,
    ).add(range(10))

    chunked_buffer = RecognitionWindowBuffer(
        min_samples=4,
        max_samples=8,
        hop_samples=2,
    )
    chunked = []

    chunked.extend(chunked_buffer.add(range(3)))
    chunked.extend(chunked_buffer.add(range(3, 7)))
    chunked.extend(chunked_buffer.add(range(7, 10)))

    assert chunked == one_shot

@pytest.mark.parametrize(
    ("min_samples", "max_samples", "hop_samples"),
    [
        (0, 8, 2),
        (8, 4, 2),
        (4, 8, 0),
    ],
)
def test_rejects_invalid_configuration(min_samples:int, max_samples: int, hop_samples:int) -> None:
    with pytest.raises(ValueError):
        RecognitionWindowBuffer(
            min_samples=min_samples,
            max_samples=max_samples,
            hop_samples=hop_samples,
        )