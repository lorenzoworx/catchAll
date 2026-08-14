import pytest

from catchall import _core


def test_native_ring_round_trip() -> None:
    ring = _core.AudioRing(4)

    accepted = ring.write([1.0, 2.0, 3.0])

    assert accepted == 3
    assert ring.capacity == 4
    assert ring.size == 3
    assert ring.read(3) == pytest.approx([1.0, 2.0, 3.0])
    assert ring.size == 0

def test_native_ring_rejects_overflow() -> None:
    ring = _core.AudioRing(3)

    accepted = ring.write([1.0, 2.0, 3.0, 4.0, 5.0])

    assert accepted == 3
    assert ring.dropped_samples == 2
    assert ring.read(3) == pytest.approx([1.0, 2.0, 3.0])

def test_native_ring_insufficient_read_returns_none() -> None:
    ring = _core.AudioRing(4)
    ring.write([1.0, 2.0])

    assert ring.read(3) is None
    assert ring.size == 2