import struct

import pytest

from catchall.audio_protocol import (
    AUDIO_FRAME_TYPE,
    AUDIO_HEADER,
    AudioFrameError,
    decode_audio_frame,
)


def make_frame(samples: list[int], first_sample_index: int = 0) -> bytes:
    header = AUDIO_HEADER.pack(
        AUDIO_FRAME_TYPE,
        0,
        len(samples),
        first_sample_index,
    )
    pcm = struct.pack(f"<{len(samples)}h", *samples)
    return header + pcm

def test_decodes_pcm_audio_frame() -> None:
    frame = decode_audio_frame(
        make_frame([-32768, 0, 16384, 32767], first_sample_index=640)
    )

    assert frame.first_sample_index == 640
    assert frame.samples == pytest.approx([-1.0, 0.0, 0.5, 32767 / 32768])

def test_rejects_short_header() -> None:
    with pytest.raises(AudioFrameError, match="shorter than"):
        decode_audio_frame(b"\x01")

def test_rejects_unknown_frame_type() -> None:
    payload = bytearray(make_frame([0]))
    payload[0] = 99

    with pytest.raises(AudioFrameError, match="frame type"):
        decode_audio_frame(bytes(payload))

def test_rejects_incorrect_payload_length() -> None:
    payload = make_frame([1, 2, 3])

    with pytest.raises(AudioFrameError, match="length"):
        decode_audio_frame(payload[:-1])