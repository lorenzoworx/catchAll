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


@dataclass(frozen=True)
class ConnectionSettings:
    """Limits for hosting CatchAll where other people can reach it."""

    max_sessions: int = 2
    allowed_origins: tuple[str, ...] = ()

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> ConnectionSettings:
        source = os.environ if environ is None else environ

        raw_max_sessions = source.get("CATCHALL_MAX_SESSIONS", "").strip()
        max_sessions = cls.max_sessions

        if raw_max_sessions:
            try:
                max_sessions = int(raw_max_sessions)
            except ValueError as error:
                raise ValueError("CATCHALL_MAX_SESSIONS must be a whole number") from error

            if max_sessions < 1:
                raise ValueError("CATCHALL_MAX_SESSIONS must be at least 1")

        allowed_origins = tuple(
            origin.strip().rstrip("/").lower()
            for origin in source.get("CATCHALL_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )

        return cls(
            max_sessions=max_sessions,
            allowed_origins=allowed_origins,
        )
