from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RecognitionSettings:
    model_name: str = "tiny.en"
    device: str = "cpu"
    compute_type: str = "int8"

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> RecognitionSettings:
        source = os.environ if environ is None else environ

        return cls(
            model_name=source.get(
                "CATCHALL_WHISPER_MODEL",
                cls.model_name,
            ),
            device=source.get(
                "CATCHALL_WHISPER_DEVICE",
                cls.device,
            ),
            compute_type=source.get(
                "CATCHALL_WHISPER_COMPUTE_TYPE",
                cls.compute_type,
            ),
        )