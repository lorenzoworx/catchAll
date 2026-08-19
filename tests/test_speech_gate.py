import pytest

from catchall.speech_gate import EnergySpeechGate


def make_gate() -> EnergySpeechGate:
    return EnergySpeechGate(
        threshold=0.05,
        frame_samples=4,
        lookback_samples=8,
        min_active_frames=2,
    )

def test_rejects_silence() -> None:
    assert make_gate().has_speech([0.0] * 8) is False

def test_accepts_multiple_active_frames() -> None:
    assert make_gate().has_speech([0.1] * 8) is True

def test_rejects_single_transient_frame() -> None:
    samples = [0.2] * 4 + [0.0] * 4
    assert make_gate().has_speech(samples) is False

def test_only_considers_recent_audio() -> None:
    samples = [0.2] * 8 + [0.0] * 8
    assert make_gate().has_speech(samples) is False

def test_rejects_incomplete_audio() -> None:
    assert make_gate().has_speech([0.2] * 3) is False


@pytest.mark.parametrize(
    (
        "threshold",
        "frame_samples",
        "lookback_samples",
        "min_active_frames",
    ),
    [
        (-0.1, 4, 8, 1),
        (0.1, 0, 8, 1),
        (0.1, 4, 2, 1),
        (0.1, 4, 8, 0),
        (0.1, 4, 8, 3),
    ],
)
def test_rejects_invalid_configuration(threshold: float, frame_samples: int, lookback_samples: int, min_active_frames: int) -> None:
    with pytest.raises(ValueError):
        EnergySpeechGate(
            threshold=threshold,
            frame_samples=frame_samples,
            lookback_samples=lookback_samples,
            min_active_frames=min_active_frames
        )