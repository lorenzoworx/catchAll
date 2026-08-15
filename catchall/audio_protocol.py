import struct
from dataclasses import dataclass

AUDIO_FRAME_TYPE = 1
AUDIO_HEADER = struct.Struct("<BBHQ")
MAX_SAMPLES_PER_FRAME = 4096


class AudioFrameError(ValueError):
    """Raided when a binary audio frame violates the wire protocol."""

@dataclass(frozen=True)
class AudioFrame:
    first_sample_index: int
    samples: tuple[float, ...]


def decode_audio_frame(payload: bytes) -> AudioFrame:
    if len(payload) < AUDIO_HEADER.size:
        raise AudioFrameError("audio frame is shorter than its header")

    frame_type, flags, sample_count, first_sample_index =  AUDIO_HEADER.unpack_from(
        payload
    )

    if frame_type != AUDIO_FRAME_TYPE:
        raise AudioFrameError("unsupported binary frame type")

    if flags != 0:
        raise AudioFrameError("unsupported audio frame flags")

    if sample_count == 0:
        raise AudioFrameError("audio frame contains no samples")

    if sample_count > MAX_SAMPLES_PER_FRAME:
        raise AudioFrameError("audio frame exceed the sample limit")

    expected_length = AUDIO_HEADER.size + sample_count * 2

    if len(payload) != expected_length:
        raise AudioFrameError("audio payload length does not match its header")

    pcm_samples = struct.unpack_from(
        f"<{sample_count}h",
        payload,
        AUDIO_HEADER.size,
    )

    normalized = tuple(sample / 32768.0 for sample in pcm_samples)

    return AudioFrame(
        first_sample_index=first_sample_index,
        samples=normalized,
    )