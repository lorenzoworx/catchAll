"""Admission control for caption WebSocket sessions.

Every session runs speech recognition on the host's CPU. A public deployment
therefore needs to bound how many sessions run at once, and to refuse pages on
other sites that try to open sessions from a visitor's browser.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit


def normalize_origin(origin: str) -> str:
    return origin.strip().rstrip("/").lower()


def origin_allowed(
    origin: str | None,
    request_hosts: Iterable[str | None],
    allowed_origins: tuple[str, ...] = (),
) -> bool:
    """Return whether a WebSocket handshake's Origin may open a session.

    Browsers always send Origin on WebSocket handshakes, so a missing header
    means a non-browser client, which no other website can be driving.

    With an explicit allow-list, only those origins are accepted. Otherwise the
    origin must name the host the request was sent to: the Host header, or the
    X-Forwarded-Host set by a reverse proxy. A page on another site cannot set
    either header from a visitor's browser.
    """

    if origin is None:
        return True

    normalized = normalize_origin(origin)

    if allowed_origins:
        return normalized in allowed_origins

    origin_host = urlsplit(normalized).netloc

    if not origin_host:
        return False

    hosts = {host.strip().lower() for host in request_hosts if host}

    return origin_host in hosts


class SessionLimiter:
    """Counts active caption sessions against a fixed capacity.

    The app runs on one event loop and nothing awaits between the check and
    the increment, so no lock is needed.
    """

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("Session capacity must be at least 1")

        self.capacity = capacity
        self._active = 0

    @property
    def active(self) -> int:
        return self._active

    def try_acquire(self) -> bool:
        if self._active >= self.capacity:
            return False

        self._active += 1
        return True

    def release(self) -> None:
        if self._active == 0:
            raise RuntimeError("Released a session that was never acquired")

        self._active -= 1
